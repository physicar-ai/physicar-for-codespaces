"""Live web view for this project, shown in the MYAPP tab (port 5000):
the camera frame with every YOLO detection drawn on it -- the target
class highlighted, everything else dimmed.

The page fits the viewport with no scrolling. If port 5000 is already
taken by another app the view is skipped with a notice, and run.py
keeps running normally.
"""
import socket
import threading

import cv2

_frame = [b""]          # latest annotated camera frame as JPEG
_data = [{}]            # latest status


def update(img_bgr, detections, target, status):
    """detections: list of (class name, confidence, (x1, y1, x2, y2))."""
    img = img_bgr.copy()
    for name, conf, (x1, y1, x2, y2) in detections:
        hit = name == target
        color = (90, 200, 255) if hit else (90, 90, 90)
        cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color,
                      2 if hit else 1)
        cv2.putText(img, f"{name} {conf:.2f}", (int(x1), int(y1) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    _frame[0] = cv2.imencode(".jpg", img)[1].tobytes()
    _data[0] = {"status": status}


def serve():
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
    from flask import Flask, Response, jsonify
    app = Flask(__name__)

    @app.get("/")
    def page():
        return _HTML

    @app.get("/frame")
    def frame():
        return Response(_frame[0], mimetype="image/jpeg",
                        headers={"Cache-Control": "no-store"})

    @app.get("/data")
    def data():
        return jsonify(_data[0])

    threading.Thread(target=lambda: app.run(
        host="0.0.0.0", port=5000, threaded=True, use_reloader=False),
        daemon=True).start()
    print("web view: open the MYAPP tab to watch")
    return True


_HTML = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>object following</title>
<style>
  html, body { height: 100%; }
  body { margin: 0; background: #14161a; overflow: hidden; }
  #wrap { position: relative; width: 100%; height: 100%; }
  img { width: 100%; height: 100%; object-fit: contain; display: block; }
  #status { position: absolute; top: 8px; left: 8px;
            background: rgba(0,0,0,0.55); color: #eee; padding: 3px 10px;
            border-radius: 6px; font: 13px/1.6 system-ui, sans-serif;
            font-variant-numeric: tabular-nums; }
</style>
<div id="wrap">
  <img id="cam" alt="">
  <div id="status">waiting for frames...</div>
</div>
<script>
var cam = document.getElementById('cam');
(function loop() {   // double-buffered: swap only after the new frame decoded
  var im = new Image();
  im.onload = function() { cam.src = im.src; setTimeout(loop, 100); };
  im.onerror = function() { setTimeout(loop, 400); };
  im.src = 'frame?_=' + Date.now();
})();
setInterval(function() {
  fetch('data').then(function(r) { return r.json(); }).then(function(d) {
    if (d.status) document.getElementById('status').textContent = d.status;
  }).catch(function() {});
}, 300);
</script>
"""
