"""
app.py — entry point. Creates the Flask app + SocketIO server and wires in the
game handlers. Run from src/:

    python app.py

then connect a Socket.IO client to http://localhost:5000.

Why not gunicorn? This game keeps all state in memory (the `rooms` dict in
session.py), so it MUST run as a single process — a multi-worker setup would
scatter players across workers that can't see each other's rooms. flask-socketio's
own server (started by socketio.run) is the supported single-process option and
speaks WebSocket out of the box (via simple-websocket). Plain gunicorn sync
workers can't serve Socket.IO at all.
"""
import os
from flask import Flask, render_template
from flask_socketio import SocketIO

from game_socket import register_handlers

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-me"   # signs the session cookie

# cors_allowed_origins="*" lets a browser client on any origin connect — fine
# for local dev, lock this down before deploying.
socketio = SocketIO(app, cors_allowed_origins="*")

# Attach every @socketio.on(...) handler defined in game_socket.py.
register_handlers(socketio)


@app.route("/")
def index():
    # Serves templates/index.html — the single-page game client. It pulls in
    # static/style.css + static/game.js and talks to the server over Socket.IO.
    return render_template("index.html")


if __name__ == "__main__":
    # Config via env so the same file works for local dev and in Docker:
    #   PORT        - port to bind (default 5000)
    #   FLASK_DEBUG - "1" enables the debugger + auto-reloader (default on).
    #                 The container sets it to "0" — the reloader forks a child
    #                 process, which is the wrong thing to do as a container's PID 1.
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    # socketio.run replaces app.run — it starts the WebSocket-capable server.
    # allow_unsafe_werkzeug lets the bundled Werkzeug server run; fine for a
    # single-process game like this, just not for high-traffic production.
    socketio.run(app, host="0.0.0.0", port=port, debug=debug, allow_unsafe_werkzeug=True)
