"""Live web views for this project, shown in the MYAPP tab (port 5000).

serve_labeling()  -- 1_labeling.py: photos collected per action + last shot
serve_dashboard() -- 2_train.py:    validation-accuracy chart per epoch
serve_monitor()   -- 3_run.py:      action probabilities, live

Pages fit the viewport with no scrolling. The camera is not duplicated
here -- app.physicar already streams it next to the tab (the labeling
page shows the last SAVED photo, which is different from the stream).
If port 5000 is already taken by another app the view is skipped with a
notice, and the calling script keeps running normally.
"""
import socket
import threading

import cv2

from model import ACTIONS

_counts = [{}]          # photos on disk per action key
_epochs = []            # validation accuracy per finished epoch
_status = [""]          # one-line status
_frame = [b""]          # last saved photo as JPEG
_infer = [{}]           # latest inference result

_ACTION_LIST = [{"key": k, **v} for k, v in ACTIONS.items()]


def set_counts(counts):
    _counts[0] = dict(counts)


def shot(key, img_bgr):
    _counts[0][key] = _counts[0].get(key, 0) + 1
    _frame[0] = cv2.imencode(".jpg", img_bgr)[1].tobytes()


def add_epoch(accuracy):
    _epochs.append({"epoch": len(_epochs) + 1,
                    "accuracy": round(float(accuracy), 3)})


def set_status(text):
    _status[0] = str(text)


def update(probs, action):
    _infer[0] = {"probs": [round(float(p), 3) for p in probs],
                 "action": int(action)}


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
    from flask import Flask, Response, jsonify
    app = Flask(__name__)

    @app.get("/")
    def index():
        return page

    @app.get("/frame")
    def frame():
        return Response(_frame[0], mimetype="image/jpeg",
                        headers={"Cache-Control": "no-store"})

    @app.get("/data")
    def data():
        return jsonify({"counts": _counts[0], "epochs": _epochs,
                        "status": _status[0], "actions": _ACTION_LIST,
                        **_infer[0]})
    return app


def serve_labeling():
    return _start(_app(_LABELING_HTML))


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

_LABELING_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>labeling</title>
<style>""" + _STYLE + """
  .nums { display: flex; gap: 28px; flex: none; }
  .nums b { font-size: 18px; font-variant-numeric: tabular-nums; }
  .nums span { display: block; font-size: 11px; color: #6f7a87; }
  #photo { flex: 1; min-height: 0; background: #1b1e24; border-radius: 10px;
           display: flex; align-items: center; justify-content: center; }
  img { max-width: 100%; max-height: 100%; border-radius: 6px; }
</style>
<main>
  <div id="status">press 1/2/3 in the terminal to collect photos</div>
  <div class="nums" id="counts"></div>
  <div id="photo"><img id="cam" alt="last saved photo"></div>
</main>
<script>
var cam = document.getElementById('cam'), last = -1;
setInterval(function() {
  fetch('data').then(function(r) { return r.json(); }).then(function(d) {
    var total = 0;
    document.getElementById('counts').innerHTML = d.actions.map(function(a) {
      var n = d.counts[a.key] || 0; total += n;
      var name = a.steering > 0 ? 'left' : a.steering < 0 ? 'right' : 'straight';
      return '<div><b>' + n + '</b><span>[' + a.key + '] ' + name + '</span></div>';
    }).join('');
    document.getElementById('status').textContent =
      total + ' photos in data/ — last saved photo below';
    if (total !== last) {   // refresh only when a new photo arrives
      last = total;
      var im = new Image();
      im.onload = function() { cam.src = im.src; };
      im.src = 'frame?_=' + Date.now();
    }
  }).catch(function() {});
}, 500);
</script>
"""

_DASHBOARD_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>training</title>
<style>""" + _STYLE + """
  #chartbox { flex: 1; min-height: 0; background: #1b1e24; border-radius: 10px;
              padding: 10px; box-sizing: border-box; }
  canvas { width: 100%; height: 100%; display: block; }
</style>
<main>
  <div id="status">waiting for the first epoch...</div>
  <div id="chartbox"><canvas id="chart"></canvas></div>
</main>
<script>
var c = document.getElementById('chart');
function draw(eps) {
  c.width = c.clientWidth * 2; c.height = c.clientHeight * 2;
  var ctx = c.getContext('2d');
  if (eps.length < 2) return;
  var px = function(i) { return 8 + i / (eps.length - 1) * (c.width - 16); };
  var py = function(a) { return 10 + (1 - a) * (c.height - 20); };
  ctx.lineWidth = 4; ctx.strokeStyle = '#5aa9e6'; ctx.beginPath();
  eps.forEach(function(e, i) { ctx[i ? 'lineTo' : 'moveTo'](px(i), py(e.accuracy)); });
  ctx.stroke();
}
setInterval(function() {
  fetch('data').then(function(r) { return r.json(); }).then(function(d) {
    if (d.status) document.getElementById('status').textContent = d.status;
    draw(d.epochs);
  }).catch(function() {});
}, 1000);
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
  .bar span { width: 110px; color: #9aa4b2; text-align: right; }
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
      '[' + a.key + '] steering ' + a.steering.toFixed(0) + '° · speed '
      + a.speed.toFixed(1) + ' m/s';
    document.getElementById('bars').innerHTML = d.actions.map(function(act, i) {
      var name = act.steering > 0 ? 'left' : act.steering < 0 ? 'right' : 'straight';
      return '<div class="bar' + (i === d.action ? ' on' : '') + '">'
        + '<span>[' + act.key + '] ' + name + ' ' + act.steering.toFixed(0) + '°</span>'
        + '<div class="track"><i style="width:' + (d.probs[i] * 100).toFixed(1) + '%"></i></div>'
        + '<b>' + (d.probs[i] * 100).toFixed(0) + '%</b></div>';
    }).join('');
  }).catch(function() {});
}, 200);
</script>
"""
