# Base image: official Python 3.13 slim (Debian-based, no extra bloat)
# We use 3.13 since 3.14 has no official Docker image yet (still in beta)
FROM python:3.13-slim

# All subsequent commands run from /app inside the container
WORKDIR /app

# Copy dependency list first — so Docker can cache this layer separately.
# If your code changes but requirements.txt doesn't, pip install is skipped.
COPY requirements.txt .

# Install dependencies into the container.
# --no-cache-dir keeps the image smaller (no pip cache stored).
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source code into the container
COPY src/ ./src/

# Turn off the auto-reloader/debugger inside the container (see app.py). The
# reloader spawns a child process, which doesn't behave well as a container's
# main process and would respond poorly to `docker stop`.
ENV FLASK_DEBUG=0

# Document that the app listens on 5000 (doesn't actually open the port —
# publishing is done in docker-compose.yml / `docker run -p`).
EXPOSE 5000

# Run the flask-socketio server directly. We DON'T use gunicorn:
#   * this game keeps all state in memory, so it must be ONE process (gunicorn's
#     worker model would split players across processes that can't see each other)
#   * plain gunicorn sync workers can't serve Socket.IO / WebSocket at all
# Running the script puts /app/src on sys.path, so app.py's top-level imports
# (from game_socket import …, import session, …) resolve correctly.
CMD ["python", "src/app.py"]
