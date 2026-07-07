FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rooms.py server.py ./
COPY static/ static/

RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 5000

# Single worker (in-memory room state), many threads; simple-websocket
# provides WebSocket support in Flask-SocketIO's threading mode.
CMD exec gunicorn -w 1 --threads 100 -b 0.0.0.0:${PORT:-5000} server:app
