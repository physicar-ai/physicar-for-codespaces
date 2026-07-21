import os

from flask import Flask, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/<path:name>")
def static_file(name):
    return send_from_directory(HERE, name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
