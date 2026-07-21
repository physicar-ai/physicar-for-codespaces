"""Live web views for this project, shown in the MYAPP tab (port 5000).

serve_dashboard() -- 1_train.py: episode-reward chart + training status
serve_monitor()   -- 2_run.py:   action probabilities, live

Pages fit the viewport with no scrolling. The camera is not duplicated
here -- app.physicar already streams it next to the tab.
If port 5000 is already taken by another app the view is skipped with a
notice, and the calling script keeps running normally.
"""
import socket
import threading

from model import ACTIONS

_episodes = []          # {"episode", "reward", "steps"} per finished episode
_status = [""]          # one-line training status
_infer = [{}]           # latest inference result


def set_status(text):
    _status[0] = str(text)


def add_episode(reward, steps):
    _episodes.append({"episode": len(_episodes) + 1,
                      "reward": round(float(reward), 2), "steps": int(steps)})


def update(probs, action):
    _infer[0] = {"probs": [round(float(p), 3) for p in probs],
                 "action": int(action),
                 "actions": ACTIONS}


def _start(app):
    try:
        probe = socket.socket()
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("", 5000))
        probe.close()
    except OSError:
        print("web view: port 5000 is in use -- skipping")
        return False
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    threading.Thread(target=lambda: app.run(
        host="0.0.0.0", port=5000, threaded=True, use_reloader=False),
        daemon=True).start()
    print("web view: open the MYAPP tab to watch")
    return True


def _app(page):
    from flask import Flask, jsonify
    app = Flask(__name__)

    @app.get("/")
    def index():
        return page

    @app.get("/data")
    def data():
        return jsonify({"episodes": _episodes, "status": _status[0],
                        **_infer[0]})
    return app


def serve_dashboard():
    return _start(_app(_DASHBOARD_HTML))


def serve_monitor():
    return _start(_app(_MONITOR_HTML))


_STYLE = """
  html, body { height: 100%; }
  body { margin: 0; background: #14161a; color: #dfe3e8; overflow: hidden;
         font: 13px/1.4 system-ui, sans-serif; }
  main { height: 100%; box-sizing: border-box; padding: 12px 14px;
         display: flex; flex-direction: column; gap: 10px; }
  #status { color: #6f7a87; font-variant-numeric: tabular-nums; flex: none; }
"""

_DASHBOARD_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>training</title>
<style>""" + _STYLE + """
  .nums { display: flex; gap: 28px; flex: none; }
  .nums b { font-size: 18px; font-variant-numeric: tabular-nums; }
  .nums span { display: block; font-size: 11px; color: #6f7a87; }
  #chartbox { flex: 1; min-height: 0; background: #1b1e24; border-radius: 10px;
              padding: 10px; box-sizing: border-box; }
  canvas { width: 100%; height: 100%; display: block; }
</style>
<main>
  <div id="status">waiting for the first episode...</div>
  <div class="nums">
    <div><b id="n-ep">0</b><span>episodes</span></div>
    <div><b id="n-last">-</b><span>last reward</span></div>
    <div><b id="n-best">-</b><span>best reward</span></div>
  </div>
  <div id="chartbox"><canvas id="chart"></canvas></div>
</main>
<script>
var c = document.getElementById('chart');
function draw(eps) {
  c.width = c.clientWidth * 2; c.height = c.clientHeight * 2;
  var ctx = c.getContext('2d');
  if (eps.length < 2) return;
  var rs = eps.map(function(e) { return e.reward; });
  var lo = Math.min.apply(null, rs), hi = Math.max.apply(null, rs);
  if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
  var px = function(i) { return 8 + i / (eps.length - 1) * (c.width - 16); };
  var py = function(r) { return 10 + (1 - (r - lo) / (hi - lo)) * (c.height - 20); };
  ctx.lineWidth = 2; ctx.strokeStyle = '#3d4654'; ctx.beginPath();
  rs.forEach(function(r, i) { ctx[i ? 'lineTo' : 'moveTo'](px(i), py(r)); });
  ctx.stroke();
  // rolling mean over the last 10 episodes: the actual learning trend
  ctx.lineWidth = 4; ctx.strokeStyle = '#5aa9e6'; ctx.beginPath();
  rs.forEach(function(_, i) {
    var w = rs.slice(Math.max(0, i - 9), i + 1);
    var m = w.reduce(function(a, b) { return a + b; }, 0) / w.length;
    ctx[i ? 'lineTo' : 'moveTo'](px(i), py(m));
  });
  ctx.stroke();
}
setInterval(function() {
  fetch('data').then(function(r) { return r.json(); }).then(function(d) {
    if (d.status) document.getElementById('status').textContent = d.status;
    var eps = d.episodes;
    document.getElementById('n-ep').textContent = eps.length;
    if (eps.length) {
      document.getElementById('n-last').textContent = eps[eps.length - 1].reward.toFixed(1);
      document.getElementById('n-best').textContent =
        Math.max.apply(null, eps.map(function(e) { return e.reward; })).toFixed(1);
    }
    draw(eps);
  }).catch(function() {});
}, 2000);
</script>
"""

_MONITOR_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>driving</title>
<style>""" + _STYLE + """
  #bars { flex: 1; display: flex; flex-direction: column;
          justify-content: center; gap: 14px; }
  .bar { display: flex; align-items: center; gap: 12px;
         font-variant-numeric: tabular-nums; }
  .bar span { width: 100px; color: #9aa4b2; text-align: right; }
  .bar .track { flex: 1; height: 22px; background: #1b1e24; border-radius: 5px; }
  .bar i { display: block; height: 100%; border-radius: 5px; background: #3d4654;
           transition: width 0.15s; }
  .bar.on i { background: #5aa9e6; }
  .bar b { width: 44px; color: #6f7a87; font-weight: 400; }
</style>
<main>
  <div id="status">waiting for the model...</div>
  <div id="bars"></div>
</main>
<script>
setInterval(function() {
  fetch('data').then(function(r) { return r.json(); }).then(function(d) {
    if (d.action === undefined) return;
    var a = d.actions[d.action];
    document.getElementById('status').textContent =
      'steering ' + (a.steering > 0 ? 'left ' : a.steering < 0 ? 'right ' : 'straight ')
      + a.steering.toFixed(0) + '° · speed ' + a.speed.toFixed(1) + ' m/s';
    document.getElementById('bars').innerHTML = d.actions.map(function(act, i) {
      var name = act.steering > 0 ? 'left' : act.steering < 0 ? 'right' : 'straight';
      return '<div class="bar' + (i === d.action ? ' on' : '') + '">'
        + '<span>' + name + ' ' + act.steering.toFixed(0) + '°</span>'
        + '<div class="track"><i style="width:' + (d.probs[i] * 100).toFixed(1) + '%"></i></div>'
        + '<b>' + (d.probs[i] * 100).toFixed(0) + '%</b></div>';
    }).join('');
  }).catch(function() {});
}, 200);
</script>
"""
