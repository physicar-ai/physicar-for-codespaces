const INSTRUCTIONS = `
You are PhysiCar, a self-driving robot. Respond in the user's language, short and friendly.
When asked to act, you MUST call a tool — never just say you will and skip the call.
Drive gently — use speed 0.5 m/s by default; go faster only if the user insists.
To actually go somewhere, always pass duration (seconds) — a speed without
duration expires after ~1 s (safety watchdog) and the car stops by itself.
When told to stop, immediately call drive(speed=0, steering=0).
"What do you see?" → call camera first, then answer. "Anything around me?" → read lidar.
For music: find it with music_search, then play with music_player(action=play).
`;

const TOOLS = {

  drive: {
    description: 'Set speed and steering. Without duration the speed expires after ~1 s (safety watchdog) and the car stops — pass duration to keep driving; the server auto-stops at the end and the call returns when the drive is done. e.g. forward 3 s turning right: drive(speed=0.5, steering=-10, duration=3). stop now: drive(speed=0, steering=0)',
    properties: [
      { name: 'speed', type: 'number', description: 'm/s (-3..3, +=forward; 0.5 recommended)' },
      { name: 'steering', type: 'number', description: 'degrees (-20..20, +=left)' },
      { name: 'duration', type: 'number', description: 'seconds to hold the speed (1..120); the server keeps it alive and stops the car at the end' },
    ],
    run: async ({speed = 0, steering = 0, duration}) => {
      await fetch('/steering', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({value: steering * Math.PI / 180})});  // API wants radians
      const body = {value: speed};
      if (duration) body.duration = Math.max(1, Math.min(120, duration));
      // With duration this response blocks until the car has stopped —
      // chain the next action directly, no sleep needed.
      await fetch('/speed', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)});
      return `speed ${speed} m/s, steering ${steering} deg`
        + (duration ? `, drove ${body.duration} s and stopped` : '');
    },
  },

  look: {
    description: 'Rotate the camera. pan=left/right, tilt=up/down.',
    properties: [
      { name: 'pan', type: 'number', description: 'camera pan degrees (-30..30, +=left)' },
      { name: 'tilt', type: 'number', description: 'camera tilt degrees (-30..30, +=up)' },
    ],
    run: async ({pan = 0, tilt = 0}) => {
      await fetch('/camera/pan', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({value: pan * Math.PI / 180})});
      await fetch('/camera/tilt', {method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({value: tilt * Math.PI / 180})});
      return `pan ${pan} deg, tilt ${tilt} deg`;
    },
  },

  sleep: {
    description: 'Wait for a given duration. Use between tool calls to create timed sequences, e.g. play music → sleep(5) → stop. For driving, prefer drive(duration=...) instead.',
    properties: [
      { name: 'seconds', type: 'number', description: 'seconds to wait (0.1~60)' },
    ],
    run: async ({seconds = 1}) => {
      await new Promise(r => setTimeout(r, Math.max(0.1, Math.min(60, seconds)) * 1000));
      return 'done';
    },
  },

  camera: {
    description: 'Capture an image from the front camera. The photo is added to the conversation.',
    properties: [],
    run: async () => {
      const blob = await (await fetch('/camera')).blob();
      const dataUrl = await new Promise(res => {
        const fr = new FileReader(); fr.onload = () => res(fr.result);
        fr.readAsDataURL(blob);
      });
      return { output: 'Photo taken. Describe what is in the image right away.',
               image: dataUrl.split(',')[1] };
    },
  },

  lidar: {
    description: 'Read 360° LiDAR distance scan. Returns angle→distance(m) map. 0°=front, +90°=left, -90°=right, 180°=rear. Range: 0.15m ~ 16m.',
    properties: [
      { name: 'step', type: 'number', description: 'angular step in degrees (0.5~30, default 5)' },
    ],
    run: async ({step = 5}) => {
      const r = await fetch('/lidar?step=' + step);
      return JSON.stringify(await r.json());
    },
  },

  states: {
    description: 'Read robot states: speed, steering, camera pan/tilt, and battery.',
    properties: [],
    run: async () => {
      const speed = await (await fetch('/speed')).json();
      const steering = await (await fetch('/steering')).json();
      const pan = await (await fetch('/camera/pan')).json();
      const tilt = await (await fetch('/camera/tilt')).json();
      const battery = await (await fetch('/battery')).json();
      return JSON.stringify({
        speed,
        steering_deg: Math.round(steering * 180 / Math.PI * 10) / 10,
        pan_deg: Math.round(pan * 180 / Math.PI * 10) / 10,
        tilt_deg: Math.round(tilt * 180 / Math.PI * 10) / 10,
        battery,
      });
    },
  },

  music_search: {
    description: 'Search iTunes for music tracks. Use the preview_url with music_player.',
    properties: [
      { name: 'query', type: 'string', description: 'search query', required: true },
    ],
    // iTunes has no CORS headers — classic JSONP (script tag + callback).
    run: ({query}) => new Promise((resolve) => {
      const cb = 'itunes_cb_' + Date.now();
      window[cb] = (data) => {
        delete window[cb]; script.remove();
        resolve(JSON.stringify({
          results: (data.results || []).filter(t => t.previewUrl).map(t => ({
            title: t.trackName, artist: t.artistName, album: t.collectionName,
            preview_url: t.previewUrl, view_url: t.trackViewUrl,
          })),
          attribution: 'Preview provided courtesy of iTunes.',
        }));
      };
      const script = document.createElement('script');
      script.src = 'https://itunes.apple.com/search?media=music&limit=5&callback=' + cb
                   + '&term=' + encodeURIComponent(query || '');
      script.onerror = () => { delete window[cb]; script.remove();
                               resolve('search failed (network)'); };
      document.head.appendChild(script);
    }),
  },

  music_player: {
    description: 'Control music playback on the robot speaker. Use music_search first to get the preview URL.',
    properties: [
      { name: 'action', type: 'string', description: 'play / stop / volume / status', required: true },
      { name: 'url', type: 'string', description: 'preview URL from music_search' },
      { name: 'volume', type: 'number', description: '0.0~1.0 (default 0.5)' },
    ],
    run: async ({action, url, volume = 0.5}) => {
      volume = Math.max(0, Math.min(1, volume));
      if (action === 'play') {
        if (!url) return 'url required';
        const r = await (await fetch('/audio/play', {method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url, volume, replace: true})})).json();
        TOOLS.music_player._id = r.id;
        return 'playback started';
      }
      if (action === 'stop') {
        await fetch('/audio/stop', {method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({all: true})});
        TOOLS.music_player._id = null;
        return 'playback stopped';
      }
      if (action === 'volume') {
        if (!TOOLS.music_player._id) return 'nothing is playing';
        await fetch('/audio/volume', {method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({id: TOOLS.music_player._id, volume})});
        return `volume ${volume}`;
      }
      if (action === 'status') return JSON.stringify(await (await fetch('/audio')).json());
      return 'unknown action: ' + action + ' (use: play, stop, volume, status)';
    },
  },

};
