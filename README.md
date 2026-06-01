# PPT Remote

Control any presentation software from your phone — no local network required.

Open a browser on your phone, enter the Room ID and PIN shown in the desktop app, and use the on-screen buttons to control your slides. Works with PowerPoint, Keynote, LibreOffice Impress, and any other full-screen presentation software.

## Architecture

```
Phone browser
    │  WebSocket (wss://your-server.com)
    ▼
Gateway Server  ── public VPS, Python Flask-SocketIO
    │  WebSocket (wss://your-server.com)
    ▼
GUI App  ── presenter's computer, CustomTkinter + pystray
    │  pyautogui / ydotool
    ▼
Keyboard events → PowerPoint / Keynote / LibreOffice …
```

The phone and computer do **not** need to be on the same network.

## Quick Start

### 1. Deploy the Gateway (VPS)

```bash
# docker-compose.yml is in the repo root
docker compose up -d
```

Set a strong secret key in production:

```bash
SECRET_KEY=your-random-secret docker compose up -d
```

If the gateway sits behind a reverse proxy (nginx, Caddy), add `TRUST_PROXY=1` so IP-based rate limiting works correctly.

### 2. Run the GUI App (presenter's computer)

Download the latest release for your platform:

| Platform | File |
|----------|------|
| Windows | `ppt-remote-windows.exe` |
| macOS (Apple Silicon) | `ppt-remote-macos-arm.dmg` |
| macOS (Intel) | `ppt-remote-macos-intel.dmg` |
| Linux | `ppt-remote-linux` |

**macOS:** Open the DMG and drag `ppt-remote.app` to Applications. On first launch right-click → Open to bypass Gatekeeper (app is unsigned).

**Linux:** `chmod +x ppt-remote-linux && ./ppt-remote-linux`

Configure the Gateway URL via the **設定** button in the app window. The setting is saved to `~/.ppt-remote/config.json`.

### 3. Connect from your phone

Open `https://your-gateway.com` in your phone's browser, enter the Room ID and PIN shown in the app, and tap **連線**.

Or click **複製連結** in the app to copy a URL that pre-fills the Room ID and PIN automatically.

## Controls

| Button | Action |
|--------|--------|
| ▶ 開始簡報 | Start presentation (F5) |
| ◀ 上一頁 | Previous slide (←) |
| 下一頁 ▶ | Next slide (→) |
| ■ 結束簡報 | End presentation (Esc) |

## Configuration

### Gateway environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Listening port |
| `SECRET_KEY` | random | Flask session secret — set a fixed value in production |
| `TRUST_PROXY` | unset | Set to `1` when behind a reverse proxy to trust `X-Forwarded-For` |

### GUI App

Gateway URL is configured via the **設定** button and stored in `~/.ppt-remote/config.json`. It can also be set via the `PPT_REMOTE_GATEWAY` environment variable before first launch.

## Linux (Wayland)

The GUI App auto-detects Wayland via `$WAYLAND_DISPLAY`. On Wayland, keyboard simulation requires [`ydotool`](https://github.com/ReimuNotMoe/ydotool):

```bash
# Debian/Ubuntu
sudo apt install ydotool

# Fedora
sudo dnf install ydotool
```

On X11 (and all other platforms), `pyautogui` is used automatically — no extra setup needed.

## Building from Source

**Gateway:**
```bash
cd gateway
pip install -r requirements.txt
python server.py
```

**GUI App:**
```bash
cd gui-app
pip install -r requirements.txt
python main.py
```

**Run tests:**
```bash
cd gateway && python -m pytest tests/
cd gui-app  && python -m pytest tests/
```

**Package GUI App:**
```bash
cd gui-app
pip install pyinstaller
pyinstaller --onefile --noconsole --name ppt-remote main.py
# output: gui-app/dist/ppt-remote(.exe)
```

## Security

- Room ID + PIN double authentication required to join
- 10 failed PIN attempts → IP blocked for 60 seconds
- PIN and Room ID generated with `secrets` module (cryptographically secure)
- `SECRET_KEY` loaded from environment variable (random per-process default)
- Max 10 mobile clients per room
- Gateway container runs as non-root user
- Enable HTTPS via nginx/Caddy reverse proxy for production deployments

## Project Structure

```
ppt-remote/
├── gateway/
│   ├── server.py          # Flask-SocketIO: room management and relay
│   ├── rooms.py           # RoomManager: auth, rate limiting, state
│   ├── requirements.txt
│   └── static/
│       ├── index.html     # Mobile remote control UI
│       └── socket.io.js   # Bundled Socket.IO client
├── gui-app/
│   ├── main.py            # CustomTkinter window + pystray tray
│   ├── connector.py       # WebSocket client
│   ├── keyboard.py        # Cross-platform keystroke simulation
│   ├── config.py          # Settings persistence
│   └── requirements.txt
├── docker-compose.yml
└── .github/workflows/
    └── build.yml          # CI: build for Windows, Linux, macOS
```
