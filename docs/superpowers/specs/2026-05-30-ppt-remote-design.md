# PPT Remote Control — Design Spec

**Date:** 2026-05-30  
**Status:** Approved

---

## Overview

A cross-platform PPT remote control system allowing a mobile browser to control any full-screen presentation software on a computer via a publicly-hosted Gateway Server. The mobile device and computer do not need to be on the same local network.

---

## Architecture

```
手機瀏覽器
    │  WebSocket (wss://yourserver.com)
    ▼
Gateway Server（公網 VPS，Python Flask-SocketIO）
    │  WebSocket (wss://yourserver.com)
    ▼
GUI App（報告者電腦，CustomTkinter + pystray）
    │  pyautogui
    ▼
鍵盤事件 → 任何全螢幕簡報軟體（PowerPoint, Keynote, LibreOffice...）
```

**Three independent deployment units:**

| Unit | Runs On | Tech |
|------|---------|------|
| `gateway/` | Public VPS | Python Flask-SocketIO |
| `gui-app/` | Presenter's computer | Python CustomTkinter + pyautogui + pystray |
| `gateway/static/` | Served by Gateway | Pure HTML/CSS/JS |

---

## Connection Flow

1. Presenter runs GUI App on their computer → app connects to Gateway Server → a **Room** is created
2. GUI App window displays **Room ID** (e.g. `A7X2`) and **PIN** (e.g. `8341`)
3. Mobile browser opens the Gateway URL → enters Room ID + PIN → enters remote control UI
4. Gateway relays mobile commands to GUI App → pyautogui executes keystrokes

---

## Room Management

- GUI App connects → Gateway generates a 4-character Room ID (uppercase alphanumeric, e.g. `A7X2`)
- GUI App disconnects → Room is destroyed, mobile clients see "Host offline"
- Multiple mobile devices can connect to the same Room simultaneously; all can control

---

## WebSocket Protocol

| Direction | Event | Payload | Description |
|-----------|-------|---------|-------------|
| GUI App → Gateway | `register` | `{pin: "8341"}` | Create Room |
| Gateway → GUI App | `registered` | `{room_id: "A7X2"}` | Return Room ID |
| Mobile → Gateway | `join` | `{room_id: "A7X2", pin: "8341"}` | Join Room |
| Gateway → Mobile | `join_result` | `{success: true/false}` | Auth result |
| Mobile → Gateway | `key` | `{action: "next"}` | Key command |
| Gateway → GUI App | `key` | `{action: "next"}` | Relayed command |
| Gateway → Mobile | `ack` | `{action: "next"}` | Confirm executed |

**Supported actions:**

| Action | Key |
|--------|-----|
| `next` | → Right Arrow |
| `prev` | ← Left Arrow |
| `start` | F5 |
| `end` | Esc |

---

## Security

- Room ID + PIN double verification required to join
- PIN failure 10 times → block that IP for 60 seconds
- Gateway stores no command history
- Production deployment uses SSL (`wss://`) via nginx reverse proxy

---

## GUI App Window

```
┌─────────────────────────────────┐
│  PPT Remote                 — □ X│
├─────────────────────────────────┤
│  狀態：● 已連線 Gateway          │
│                                 │
│  Room ID    PIN                 │
│  ┌───────┐  ┌───────┐           │
│  │ A7X2  │  │ 8341  │           │
│  └───────┘  └───────┘           │
│                                 │
│  已連線手機：2 台                │
│                                 │
│  Gateway：wss://yourserver.com  │
│  ─────────────────────────────  │
│  [ 重新產生 PIN ]  [ 斷線重連 ]  │
└─────────────────────────────────┘
```

**Behaviors:**
- Close button (X) → minimize to system tray, app keeps running in background
- Tray icon right-click → menu: "Show Window" / "Quit"
- Gateway disconnect → auto-reconnect (every 5 seconds), status indicator turns red
- "重新產生 PIN" → kick all connected mobile clients, generate new PIN

**Cross-platform tray:** `pystray` (Windows, macOS, Linux with AppIndicator/GTK)

---

## Mobile UI

Two screens served as a single static HTML page (no framework, vanilla JS):

**Screen 1 — Login:**
- Room ID input
- PIN input
- Connect button

**Screen 2 — Remote Control:**
- Connection status indicator (top right)
- Start Presentation button (F5)
- Previous / Next buttons (large, thumb-friendly, min 80px tall)
- End Presentation button (Esc)
- Dark background (non-distracting during presentations)
- Auto-reconnect on WebSocket disconnect (up to 5 attempts, exponential backoff)

---

## Cross-Platform Keyboard Simulation

| Platform | Method | Dependency |
|----------|--------|------------|
| Windows | `pyautogui` | None |
| macOS | `pyautogui` | Grant Accessibility permission |
| Linux (X11) | `pyautogui` | `python3-xlib` |
| Linux (Wayland) | `subprocess` + `ydotool` | `ydotool` pre-installed |

GUI App detects platform at startup and shows a warning if additional setup is needed.

---

## Project Structure

```
ppt-remote/
├── gateway/
│   ├── server.py          # Flask-SocketIO: Room management, relay
│   ├── requirements.txt   # flask, flask-socketio
│   └── static/
│       └── index.html     # Mobile remote control page
└── gui-app/
    ├── main.py            # CustomTkinter window + pystray tray
    ├── connector.py       # WebSocket connection to Gateway
    ├── keyboard.py        # Cross-platform keystroke via pyautogui
    └── requirements.txt   # customtkinter, pystray, pyautogui, python-socketio
```

---

## Deployment

**Gateway (VPS):**
```bash
pip install -r requirements.txt
python server.py
# Recommend: nginx reverse proxy + SSL certificate (Let's Encrypt)
```

**GUI App (distribution):**
- Packaged with PyInstaller into a single executable
- Windows: `.exe`, macOS: `.app`, Linux: binary
- End users need no Python or dependency installation
