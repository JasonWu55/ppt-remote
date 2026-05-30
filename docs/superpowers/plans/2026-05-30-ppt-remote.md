# PPT Remote Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform PPT remote control system where a mobile browser controls any full-screen presentation via a publicly-hosted Gateway Server that relays WebSocket commands to a desktop GUI App running pyautogui.

**Architecture:** A Gateway Server (Flask-SocketIO) runs on a public VPS and manages Rooms. The GUI App registers a Room with a PIN; mobile browsers join the Room via Room ID + PIN. The Gateway relays `key` events from mobile to GUI App, which executes keystrokes via pyautogui. Mobile and computer do not need to be on the same network.

**Tech Stack:** Python 3.10+, Flask 3.x, Flask-SocketIO 5.x, python-socketio 5.x, CustomTkinter 5.x, pystray 0.19.x, pyautogui 0.9.x, Pillow, pytest, pytest-mock

---

## File Map

```
ppt-remote/
├── gateway/
│   ├── rooms.py                   # Pure room/IP-block logic (RoomManager)
│   ├── server.py                  # Flask-SocketIO event handlers
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── static/
│   │   └── index.html             # Mobile remote-control SPA
│   └── tests/
│       ├── test_rooms.py
│       └── test_server.py
└── gui-app/
    ├── keyboard.py                # Cross-platform keystroke (pyautogui / ydotool)
    ├── connector.py               # WebSocket client to Gateway
    ├── main.py                    # CustomTkinter window + pystray tray
    ├── requirements.txt
    ├── requirements-dev.txt
    └── tests/
        ├── test_keyboard.py
        └── test_connector.py
```

---

## Task 1: Project Setup

**Files:**
- Create: `gateway/requirements.txt`
- Create: `gateway/requirements-dev.txt`
- Create: `gateway/tests/__init__.py`
- Create: `gui-app/requirements.txt`
- Create: `gui-app/requirements-dev.txt`
- Create: `gui-app/tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p gateway/static gateway/tests
mkdir -p gui-app/tests
touch gateway/tests/__init__.py gui-app/tests/__init__.py
```

- [ ] **Step 2: Write gateway/requirements.txt**

```
flask==3.1.0
flask-socketio==5.4.1
eventlet==0.37.0
```

- [ ] **Step 3: Write gateway/requirements-dev.txt**

```
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 4: Write gui-app/requirements.txt**

```
customtkinter==5.2.2
pystray==0.19.5
pyautogui==0.9.54
python-socketio[client]==5.12.1
Pillow==11.0.0
```

- [ ] **Step 5: Write gui-app/requirements-dev.txt**

```
pytest==8.3.4
pytest-mock==3.14.0
```

- [ ] **Step 6: Install gateway dependencies**

```bash
cd gateway && pip install -r requirements.txt -r requirements-dev.txt
```

Expected: all packages install without error.

- [ ] **Step 7: Install gui-app dependencies**

```bash
cd gui-app && pip install -r requirements.txt -r requirements-dev.txt
```

Expected: all packages install without error.

- [ ] **Step 8: Commit**

```bash
git add gateway/ gui-app/
git commit -m "chore: project structure and requirements"
```

---

## Task 2: Gateway — Room Manager (Pure Logic)

**Files:**
- Create: `gateway/rooms.py`
- Create: `gateway/tests/test_rooms.py`

- [ ] **Step 1: Write the failing tests**

`gateway/tests/test_rooms.py`:
```python
import pytest
from datetime import datetime, timedelta
from rooms import RoomManager

@pytest.fixture
def rm():
    return RoomManager()

def test_create_room_returns_4char_id(rm):
    room_id = rm.create_room(gui_sid='sid-gui-1', pin='1234')
    assert len(room_id) == 4
    assert room_id.isupper() or room_id.isalnum()

def test_create_room_ids_are_unique(rm):
    ids = {rm.create_room(gui_sid=f'sid-{i}', pin='0000') for i in range(20)}
    assert len(ids) == 20

def test_join_room_valid(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    success, reason = rm.join_room(room_id=room_id, pin='1234',
                                   mobile_sid='mob-1', ip='1.2.3.4')
    assert success is True
    assert reason is None

def test_join_room_wrong_pin(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    success, reason = rm.join_room(room_id=room_id, pin='9999',
                                   mobile_sid='mob-1', ip='1.2.3.4')
    assert success is False
    assert reason == 'invalid'

def test_join_room_nonexistent(rm):
    success, reason = rm.join_room(room_id='XXXX', pin='1234',
                                   mobile_sid='mob-1', ip='1.2.3.4')
    assert success is False
    assert reason == 'invalid'

def test_ip_blocked_after_10_failures(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    for _ in range(10):
        rm.join_room(room_id=room_id, pin='wrong',
                     mobile_sid='mob-x', ip='5.6.7.8')
    success, reason = rm.join_room(room_id=room_id, pin='1234',
                                   mobile_sid='mob-1', ip='5.6.7.8')
    assert success is False
    assert reason == 'blocked'

def test_ip_block_expires(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    for _ in range(10):
        rm.join_room(room_id=room_id, pin='wrong',
                     mobile_sid='mob-x', ip='5.6.7.8')
    # Manually expire the block
    rm._ip_failures['5.6.7.8']['blocked_until'] = datetime.now() - timedelta(seconds=1)
    success, _ = rm.join_room(room_id=room_id, pin='1234',
                               mobile_sid='mob-1', ip='5.6.7.8')
    assert success is True

def test_get_gui_sid(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    assert rm.get_gui_sid(room_id) == 'gui-1'

def test_get_mobile_sids(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    rm.join_room(room_id, '1234', 'mob-1', '1.1.1.1')
    rm.join_room(room_id, '1234', 'mob-2', '2.2.2.2')
    assert rm.get_mobile_sids(room_id) == {'mob-1', 'mob-2'}

def test_remove_gui_returns_mobile_sids(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    rm.join_room(room_id, '1234', 'mob-1', '1.1.1.1')
    result = rm.remove_gui(gui_sid='gui-1')
    assert result == (room_id, {'mob-1'})
    assert room_id not in rm._rooms

def test_remove_gui_unknown_sid(rm):
    assert rm.remove_gui('nonexistent') is None

def test_remove_mobile(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    rm.join_room(room_id, '1234', 'mob-1', '1.1.1.1')
    rm.remove_mobile('mob-1')
    assert rm.get_mobile_sids(room_id) == set()

def test_get_role_gui(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    assert rm.get_role('gui-1') == ('gui', room_id)

def test_get_role_mobile(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    rm.join_room(room_id, '1234', 'mob-1', '1.1.1.1')
    assert rm.get_role('mob-1') == ('mobile', room_id)

def test_get_role_unknown(rm):
    assert rm.get_role('nobody') is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd gateway && python -m pytest tests/test_rooms.py -v
```

Expected: `ModuleNotFoundError: No module named 'rooms'`

- [ ] **Step 3: Implement gateway/rooms.py**

```python
import random
import string
from datetime import datetime, timedelta

MAX_FAILURES = 10
BLOCK_SECONDS = 60
ROOM_ID_LEN = 4


class RoomManager:
    def __init__(self):
        self._rooms = {}        # room_id -> {pin, gui_sid, mobile_sids}
        self._client_role = {}  # sid -> (role, room_id)
        self._ip_failures = {}  # ip -> {count, blocked_until}

    def create_room(self, gui_sid: str, pin: str) -> str:
        room_id = self._gen_room_id()
        self._rooms[room_id] = {'pin': pin, 'gui_sid': gui_sid, 'mobile_sids': set()}
        self._client_role[gui_sid] = ('gui', room_id)
        return room_id

    def join_room(self, room_id: str, pin: str, mobile_sid: str, ip: str):
        if self._is_blocked(ip):
            return False, 'blocked'
        if room_id not in self._rooms or self._rooms[room_id]['pin'] != pin:
            self._record_failure(ip)
            return False, 'invalid'
        self._rooms[room_id]['mobile_sids'].add(mobile_sid)
        self._client_role[mobile_sid] = ('mobile', room_id)
        return True, None

    def get_gui_sid(self, room_id: str) -> str | None:
        return self._rooms.get(room_id, {}).get('gui_sid')

    def get_mobile_sids(self, room_id: str) -> set:
        return self._rooms.get(room_id, {}).get('mobile_sids', set())

    def remove_gui(self, gui_sid: str):
        entry = self._client_role.pop(gui_sid, None)
        if entry is None:
            return None
        _, room_id = entry
        room = self._rooms.pop(room_id, None)
        if room is None:
            return None
        mobile_sids = room['mobile_sids']
        for sid in mobile_sids:
            self._client_role.pop(sid, None)
        return room_id, mobile_sids

    def remove_mobile(self, mobile_sid: str):
        entry = self._client_role.pop(mobile_sid, None)
        if entry is None:
            return
        _, room_id = entry
        if room_id in self._rooms:
            self._rooms[room_id]['mobile_sids'].discard(mobile_sid)

    def get_role(self, sid: str):
        entry = self._client_role.get(sid)
        if entry is None:
            return None
        role, room_id = entry
        return role, room_id

    def _gen_room_id(self) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            room_id = ''.join(random.choices(chars, k=ROOM_ID_LEN))
            if room_id not in self._rooms:
                return room_id

    def _is_blocked(self, ip: str) -> bool:
        entry = self._ip_failures.get(ip)
        if not entry:
            return False
        blocked_until = entry.get('blocked_until')
        if blocked_until and datetime.now() < blocked_until:
            return True
        if blocked_until:
            del self._ip_failures[ip]
        return False

    def _record_failure(self, ip: str):
        if ip not in self._ip_failures:
            self._ip_failures[ip] = {'count': 0, 'blocked_until': None}
        self._ip_failures[ip]['count'] += 1
        if self._ip_failures[ip]['count'] >= MAX_FAILURES:
            self._ip_failures[ip]['blocked_until'] = (
                datetime.now() + timedelta(seconds=BLOCK_SECONDS)
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd gateway && python -m pytest tests/test_rooms.py -v
```

Expected: all 14 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gateway/rooms.py gateway/tests/test_rooms.py
git commit -m "feat: gateway RoomManager with IP blocking"
```

---

## Task 3: Gateway — Flask-SocketIO Server

**Files:**
- Create: `gateway/server.py`
- Create: `gateway/tests/test_server.py`

- [ ] **Step 1: Write failing tests**

`gateway/tests/test_server.py`:
```python
import pytest
from unittest.mock import patch
from server import app, socketio, room_manager


@pytest.fixture(autouse=True)
def reset_state():
    room_manager._rooms.clear()
    room_manager._client_role.clear()
    room_manager._ip_failures.clear()
    yield


@pytest.fixture
def gui_client():
    app.config['TESTING'] = True
    return socketio.test_client(app)


@pytest.fixture
def mobile_client():
    return socketio.test_client(app)


def test_register_returns_room_id(gui_client):
    gui_client.emit('register', {'pin': '1234'})
    received = gui_client.get_received()
    assert received[0]['name'] == 'registered'
    assert len(received[0]['args'][0]['room_id']) == 4


def test_join_valid_credentials(gui_client, mobile_client):
    gui_client.emit('register', {'pin': '1234'})
    room_id = gui_client.get_received()[0]['args'][0]['room_id']

    mobile_client.emit('join', {'room_id': room_id, 'pin': '1234'})
    received = mobile_client.get_received()
    assert received[0]['name'] == 'join_result'
    assert received[0]['args'][0]['success'] is True


def test_join_wrong_pin(gui_client, mobile_client):
    gui_client.emit('register', {'pin': '1234'})
    room_id = gui_client.get_received()[0]['args'][0]['room_id']

    mobile_client.emit('join', {'room_id': room_id, 'pin': '9999'})
    received = mobile_client.get_received()
    assert received[0]['args'][0]['success'] is False


def test_join_nonexistent_room(mobile_client):
    mobile_client.emit('join', {'room_id': 'XXXX', 'pin': '1234'})
    received = mobile_client.get_received()
    assert received[0]['args'][0]['success'] is False


def test_key_relayed_to_gui(gui_client, mobile_client):
    gui_client.emit('register', {'pin': '1234'})
    room_id = gui_client.get_received()[0]['args'][0]['room_id']

    mobile_client.emit('join', {'room_id': room_id, 'pin': '1234'})
    mobile_client.get_received()  # clear join_result

    mobile_client.emit('key', {'action': 'next'})

    gui_received = gui_client.get_received()
    assert gui_received[0]['name'] == 'key'
    assert gui_received[0]['args'][0]['action'] == 'next'


def test_key_ack_sent_to_mobile(gui_client, mobile_client):
    gui_client.emit('register', {'pin': '1234'})
    room_id = gui_client.get_received()[0]['args'][0]['room_id']

    mobile_client.emit('join', {'room_id': room_id, 'pin': '1234'})
    mobile_client.get_received()

    mobile_client.emit('key', {'action': 'prev'})

    mob_received = mobile_client.get_received()
    assert mob_received[0]['name'] == 'ack'
    assert mob_received[0]['args'][0]['action'] == 'prev'


def test_gui_disconnect_notifies_mobile(gui_client, mobile_client):
    gui_client.emit('register', {'pin': '1234'})
    room_id = gui_client.get_received()[0]['args'][0]['room_id']

    mobile_client.emit('join', {'room_id': room_id, 'pin': '1234'})
    mobile_client.get_received()

    gui_client.disconnect()

    mob_received = mobile_client.get_received()
    assert mob_received[0]['name'] == 'host_disconnected'


def test_key_ignored_if_not_joined(mobile_client):
    mobile_client.emit('key', {'action': 'next'})
    # No crash, no relay (nothing to assert except no exception)


def test_ip_blocked_after_10_failures(gui_client):
    gui_client.emit('register', {'pin': '1234'})
    room_id = gui_client.get_received()[0]['args'][0]['room_id']

    with patch('server._get_client_ip', return_value='9.9.9.9'):
        for _ in range(10):
            c = socketio.test_client(app)
            c.emit('join', {'room_id': room_id, 'pin': 'wrong'})
            c.get_received()

        blocked = socketio.test_client(app)
        blocked.emit('join', {'room_id': room_id, 'pin': '1234'})
        received = blocked.get_received()
        assert received[0]['args'][0]['success'] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd gateway && python -m pytest tests/test_server.py -v
```

Expected: `ModuleNotFoundError: No module named 'server'`

- [ ] **Step 3: Implement gateway/server.py**

```python
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from rooms import RoomManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ppt-remote'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

room_manager = RoomManager()


def _get_client_ip() -> str:
    return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)


@socketio.on('register')
def on_register(data):
    pin = data.get('pin', '')
    room_id = room_manager.create_room(gui_sid=request.sid, pin=pin)
    join_room(room_id)
    emit('registered', {'room_id': room_id})


@socketio.on('join')
def on_join(data):
    ip = _get_client_ip()
    room_id = data.get('room_id', '')
    pin = data.get('pin', '')

    success, reason = room_manager.join_room(
        room_id=room_id, pin=pin, mobile_sid=request.sid, ip=ip
    )
    if success:
        join_room(room_id)
        gui_sid = room_manager.get_gui_sid(room_id)
        count = len(room_manager.get_mobile_sids(room_id))
        if gui_sid:
            emit('client_update', {'count': count}, to=gui_sid)
    emit('join_result', {'success': success, 'reason': reason})


@socketio.on('key')
def on_key(data):
    entry = room_manager.get_role(request.sid)
    if entry is None or entry[0] != 'mobile':
        return
    _, room_id = entry
    gui_sid = room_manager.get_gui_sid(room_id)
    if gui_sid is None:
        return
    action = data.get('action', '')
    emit('key', {'action': action}, to=gui_sid)
    emit('ack', {'action': action})


@socketio.on('disconnect')
def on_disconnect():
    entry = room_manager.get_role(request.sid)
    if entry is None:
        return
    role, _ = entry
    if role == 'gui':
        result = room_manager.remove_gui(request.sid)
        if result:
            room_id, mobile_sids = result
            for sid in mobile_sids:
                emit('host_disconnected', {}, to=sid)
    else:
        room_manager.remove_mobile(request.sid)
        gui_sid = room_manager.get_gui_sid(room_id)
        count = len(room_manager.get_mobile_sids(room_id))
        if gui_sid:
            emit('client_update', {'count': count}, to=gui_sid)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd gateway && python -m pytest tests/test_server.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gateway/server.py gateway/tests/test_server.py
git commit -m "feat: gateway Flask-SocketIO server"
```

---

## Task 4: Gateway — Mobile Web UI

**Files:**
- Create: `gateway/static/index.html`

- [ ] **Step 1: Write gateway/static/index.html**

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>PPT Remote</title>
  <script src="/socket.io/socket.io.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #1a1a1a;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    h1 { font-size: 1.4rem; margin-bottom: 24px; color: #ccc; }
    .screen { width: 100%; max-width: 360px; display: none; flex-direction: column; gap: 16px; }
    .screen.active { display: flex; }
    input {
      width: 100%; padding: 14px; border-radius: 10px;
      border: 1px solid #444; background: #2a2a2a;
      color: #fff; font-size: 1.2rem; text-align: center; letter-spacing: 4px;
    }
    .btn {
      width: 100%; padding: 20px; border-radius: 14px; border: none;
      font-size: 1.3rem; font-weight: 600; cursor: pointer; min-height: 80px;
      transition: opacity 0.1s; user-select: none;
    }
    .btn:active { opacity: 0.7; }
    .btn-primary { background: #4a90e2; color: #fff; }
    .btn-green   { background: #27ae60; color: #fff; }
    .btn-red     { background: #c0392b; color: #fff; }
    .btn-row { display: flex; gap: 12px; }
    .btn-row .btn { flex: 1; }
    .status {
      display: flex; align-items: center; gap: 8px;
      font-size: 0.9rem; color: #aaa; justify-content: center;
    }
    .dot { width: 10px; height: 10px; border-radius: 50%; background: #27ae60; }
    .dot.red { background: #c0392b; }
    .error { color: #e74c3c; text-align: center; font-size: 0.9rem; min-height: 20px; }
    label { color: #888; font-size: 0.85rem; text-align: center; }
  </style>
</head>
<body>
  <h1>PPT Remote</h1>

  <!-- Login Screen -->
  <div class="screen active" id="screen-login">
    <label>Room ID</label>
    <input type="text" id="input-room" placeholder="A7X2" maxlength="4"
           autocomplete="off" autocapitalize="characters">
    <label>PIN</label>
    <input type="tel" id="input-pin" placeholder="8341" maxlength="4">
    <button class="btn btn-primary" onclick="connect()">連線</button>
    <p class="error" id="login-error"></p>
  </div>

  <!-- Remote Control Screen -->
  <div class="screen" id="screen-remote">
    <div class="status">
      <div class="dot" id="status-dot"></div>
      <span id="status-text">已連線</span>
    </div>
    <button class="btn btn-green" onclick="sendKey('start')">▶ 開始簡報</button>
    <div class="btn-row">
      <button class="btn btn-primary" onclick="sendKey('prev')">◀ 上一頁</button>
      <button class="btn btn-primary" onclick="sendKey('next')">下一頁 ▶</button>
    </div>
    <button class="btn btn-red" onclick="sendKey('end')">■ 結束簡報</button>
  </div>

  <script>
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const socket = io(`${proto}://${location.host}`, { autoConnect: false });
    let roomId = '', pin = '', retries = 0;
    const MAX_RETRIES = 5;

    function showScreen(id) {
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.getElementById(id).classList.add('active');
    }

    function setStatus(connected) {
      const dot = document.getElementById('status-dot');
      dot.className = 'dot' + (connected ? '' : ' red');
      document.getElementById('status-text').textContent = connected ? '已連線' : '重新連線中...';
    }

    function connect() {
      roomId = document.getElementById('input-room').value.toUpperCase().trim();
      pin    = document.getElementById('input-pin').value.trim();
      document.getElementById('login-error').textContent = '';
      socket.connect();
    }

    function sendKey(action) {
      socket.emit('key', { action });
    }

    socket.on('connect', () => {
      socket.emit('join', { room_id: roomId, pin });
    });

    socket.on('join_result', (data) => {
      if (data.success) {
        retries = 0;
        showScreen('screen-remote');
        setStatus(true);
      } else {
        socket.disconnect();
        document.getElementById('login-error').textContent =
          data.reason === 'blocked' ? 'IP 已暫時封鎖，請稍後再試' : 'Room ID 或 PIN 錯誤';
      }
    });

    socket.on('host_disconnected', () => {
      setStatus(false);
      document.getElementById('status-text').textContent = '主機已離線';
    });

    socket.on('disconnect', () => {
      if (document.getElementById('screen-remote').classList.contains('active')) {
        setStatus(false);
        if (retries < MAX_RETRIES) {
          retries++;
          setTimeout(() => socket.connect(), Math.min(1000 * retries, 16000));
        }
      }
    });
  </script>
</body>
</html>
```

- [ ] **Step 2: Manually test the mobile UI**

Start the gateway server:
```bash
cd gateway && python server.py
```

Open `http://localhost:5000` in a browser. Verify:
- Login screen renders with Room ID and PIN inputs
- (You won't be able to log in yet without a GUI App connected — that's fine)
- Page is readable on a narrow viewport (resize browser to ~375px width)

- [ ] **Step 3: Commit**

```bash
git add gateway/static/index.html
git commit -m "feat: mobile remote control web UI"
```

---

## Task 5: GUI App — Keyboard Module

**Files:**
- Create: `gui-app/keyboard.py`
- Create: `gui-app/tests/test_keyboard.py`

- [ ] **Step 1: Write failing tests**

`gui-app/tests/test_keyboard.py`:
```python
import pytest
import keyboard  # imported at top level; mocks patch attributes after import


def test_press_next_calls_pyautogui(mocker):
    mock_press = mocker.patch('pyautogui.press')
    mocker.patch('keyboard._is_wayland', return_value=False)
    keyboard.press('next')
    mock_press.assert_called_once_with('right')


def test_press_prev_calls_pyautogui(mocker):
    mock_press = mocker.patch('pyautogui.press')
    mocker.patch('keyboard._is_wayland', return_value=False)
    keyboard.press('prev')
    mock_press.assert_called_once_with('left')


def test_press_start_calls_f5(mocker):
    mock_press = mocker.patch('pyautogui.press')
    mocker.patch('keyboard._is_wayland', return_value=False)
    keyboard.press('start')
    mock_press.assert_called_once_with('f5')


def test_press_end_calls_escape(mocker):
    mock_press = mocker.patch('pyautogui.press')
    mocker.patch('keyboard._is_wayland', return_value=False)
    keyboard.press('end')
    mock_press.assert_called_once_with('escape')


def test_press_unknown_action_does_nothing(mocker):
    mock_press = mocker.patch('pyautogui.press')
    mocker.patch('keyboard._is_wayland', return_value=False)
    keyboard.press('fly')
    mock_press.assert_not_called()


def test_press_next_wayland_uses_ydotool(mocker):
    mocker.patch('keyboard._is_wayland', return_value=True)
    mock_run = mocker.patch('subprocess.run')
    keyboard.press('next')
    mock_run.assert_called_once_with(['ydotool', 'key', 'KEY_RIGHT'], check=True)


def test_press_prev_wayland(mocker):
    mocker.patch('keyboard._is_wayland', return_value=True)
    mock_run = mocker.patch('subprocess.run')
    keyboard.press('prev')
    mock_run.assert_called_once_with(['ydotool', 'key', 'KEY_LEFT'], check=True)


def test_press_start_wayland(mocker):
    mocker.patch('keyboard._is_wayland', return_value=True)
    mock_run = mocker.patch('subprocess.run')
    keyboard.press('start')
    mock_run.assert_called_once_with(['ydotool', 'key', 'KEY_F5'], check=True)


def test_press_end_wayland(mocker):
    mocker.patch('keyboard._is_wayland', return_value=True)
    mock_run = mocker.patch('subprocess.run')
    keyboard.press('end')
    mock_run.assert_called_once_with(['ydotool', 'key', 'KEY_ESC'], check=True)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd gui-app && python -m pytest tests/test_keyboard.py -v
```

Expected: `ModuleNotFoundError: No module named 'keyboard'`

- [ ] **Step 3: Implement gui-app/keyboard.py**

```python
import os
import subprocess
import pyautogui

_PYAUTOGUI_MAP = {
    'next': 'right',
    'prev': 'left',
    'start': 'f5',
    'end': 'escape',
}

_YDOTOOL_MAP = {
    'next': 'KEY_RIGHT',
    'prev': 'KEY_LEFT',
    'start': 'KEY_F5',
    'end': 'KEY_ESC',
}


def _is_wayland() -> bool:
    return bool(os.environ.get('WAYLAND_DISPLAY'))


def press(action: str) -> None:
    if _is_wayland():
        key = _YDOTOOL_MAP.get(action)
        if key:
            subprocess.run(['ydotool', 'key', key], check=True)
    else:
        key = _PYAUTOGUI_MAP.get(action)
        if key:
            pyautogui.press(key)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd gui-app && python -m pytest tests/test_keyboard.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gui-app/keyboard.py gui-app/tests/test_keyboard.py
git commit -m "feat: cross-platform keyboard module"
```

---

## Task 6: GUI App — Connector Module

**Files:**
- Create: `gui-app/connector.py`
- Create: `gui-app/tests/test_connector.py`

- [ ] **Step 1: Write failing tests**

`gui-app/tests/test_connector.py`:
```python
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def callbacks():
    return {
        'on_room_ready': MagicMock(),
        'on_key': MagicMock(),
        'on_connect': MagicMock(),
        'on_disconnect': MagicMock(),
        'on_mobile_count': MagicMock(),
    }


@pytest.fixture
def mock_sio(mocker):
    return mocker.patch('socketio.Client').return_value


@pytest.fixture
def conn(mock_sio, callbacks):
    import connector
    return connector.Connector(
        gateway_url='ws://localhost:5000',
        pin='1234',
        **callbacks
    )


def test_pin_is_stored(conn):
    assert conn.pin == '1234'


def test_handle_connect_emits_register(mock_sio, conn):
    conn._handle_connect()
    mock_sio.emit.assert_called_once_with('register', {'pin': '1234'})


def test_handle_connect_calls_on_connect(callbacks, conn):
    conn._handle_connect()
    callbacks['on_connect'].assert_called_once()


def test_handle_registered_calls_on_room_ready(callbacks, conn):
    conn._handle_registered({'room_id': 'A7X2'})
    callbacks['on_room_ready'].assert_called_once_with('A7X2', '1234')


def test_handle_key_calls_on_key(callbacks, conn):
    conn._handle_key({'action': 'next'})
    callbacks['on_key'].assert_called_once_with('next')


def test_handle_disconnect_calls_on_disconnect(callbacks, conn):
    conn._handle_disconnect()
    callbacks['on_disconnect'].assert_called_once()


def test_handle_client_update_calls_on_mobile_count(callbacks, conn):
    conn._handle_client_update({'count': 3})
    callbacks['on_mobile_count'].assert_called_once_with(3)


def test_start_launches_background_thread(mock_sio, conn, mocker):
    mock_thread_cls = mocker.patch('connector.threading.Thread')
    conn.start()
    mock_thread_cls.assert_called_once()
    mock_thread_cls.return_value.start.assert_called_once()


def test_disconnect_calls_sio_disconnect(mock_sio, conn):
    conn.disconnect()
    mock_sio.disconnect.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd gui-app && python -m pytest tests/test_connector.py -v
```

Expected: `ModuleNotFoundError: No module named 'connector'`

- [ ] **Step 3: Implement gui-app/connector.py**

```python
import threading
import socketio


class Connector:
    def __init__(self, gateway_url: str, pin: str,
                 on_room_ready, on_key, on_connect, on_disconnect, on_mobile_count):
        self._gateway_url = gateway_url
        self._pin = pin
        self._on_room_ready = on_room_ready
        self._on_key = on_key
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_mobile_count = on_mobile_count
        self._sio = socketio.Client(reconnection=True, reconnection_delay=5)
        self._sio.on('connect', self._handle_connect)
        self._sio.on('registered', self._handle_registered)
        self._sio.on('key', self._handle_key)
        self._sio.on('client_update', self._handle_client_update)
        self._sio.on('disconnect', self._handle_disconnect)

    @property
    def pin(self) -> str:
        return self._pin

    def _handle_connect(self):
        self._sio.emit('register', {'pin': self._pin})
        self._on_connect()

    def _handle_registered(self, data):
        self._on_room_ready(data['room_id'], self._pin)

    def _handle_key(self, data):
        self._on_key(data['action'])

    def _handle_client_update(self, data):
        self._on_mobile_count(data['count'])

    def _handle_disconnect(self):
        self._on_disconnect()

    def start(self):
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _run(self):
        try:
            self._sio.connect(self._gateway_url)
            self._sio.wait()
        except Exception:
            pass

    def disconnect(self):
        self._sio.disconnect()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd gui-app && python -m pytest tests/test_connector.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add gui-app/connector.py gui-app/tests/test_connector.py
git commit -m "feat: WebSocket connector module"
```

---

## Task 7: GUI App — Main Window + System Tray

**Files:**
- Create: `gui-app/main.py`

- [ ] **Step 1: Write gui-app/main.py**

```python
import os
import random
import threading
import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
from connector import Connector
from keyboard import press

GATEWAY_URL = os.environ.get('PPT_REMOTE_GATEWAY', 'ws://localhost:5000')

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')


def _make_tray_icon() -> Image.Image:
    img = Image.new('RGB', (64, 64), color=(30, 30, 200))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, 56, 56], fill=(255, 255, 255))
    return img


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('PPT Remote')
        self.geometry('420x320')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        self._tray: pystray.Icon | None = None
        self._connector: Connector | None = None
        self._mobile_count = 0

        self._build_ui()
        self._start_connector()

    # ── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._status_label = ctk.CTkLabel(
            self, text='狀態：連線中...', text_color='orange')
        self._status_label.pack(pady=(20, 10))

        info = ctk.CTkFrame(self)
        info.pack(pady=6)

        ctk.CTkLabel(info, text='Room ID', text_color='gray').grid(
            row=0, column=0, padx=30)
        ctk.CTkLabel(info, text='PIN', text_color='gray').grid(
            row=0, column=1, padx=30)

        self._room_label = ctk.CTkLabel(
            info, text='----', font=ctk.CTkFont(size=28, weight='bold'))
        self._room_label.grid(row=1, column=0, padx=30, pady=6)

        self._pin_label = ctk.CTkLabel(
            info, text='----', font=ctk.CTkFont(size=28, weight='bold'))
        self._pin_label.grid(row=1, column=1, padx=30, pady=6)

        self._clients_label = ctk.CTkLabel(self, text='已連線手機：0 台')
        self._clients_label.pack(pady=4)

        self._gw_label = ctk.CTkLabel(
            self, text=f'Gateway：{GATEWAY_URL}', text_color='gray',
            font=ctk.CTkFont(size=11))
        self._gw_label.pack(pady=2)

        btn_frame = ctk.CTkFrame(self, fg_color='transparent')
        btn_frame.pack(pady=14)

        ctk.CTkButton(
            btn_frame, text='重新產生 PIN', width=140,
            command=self._regenerate_pin
        ).grid(row=0, column=0, padx=6)

        ctk.CTkButton(
            btn_frame, text='斷線重連', width=140,
            command=self._reconnect
        ).grid(row=0, column=1, padx=6)

    # ── Connector lifecycle ──────────────────────────────────────────────────

    def _new_pin(self) -> str:
        return f'{random.randint(0, 9999):04d}'

    def _start_connector(self, pin: str | None = None):
        if pin is None:
            pin = self._new_pin()
        self._connector = Connector(
            gateway_url=GATEWAY_URL,
            pin=pin,
            on_room_ready=self._on_room_ready,
            on_key=self._on_key,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
            on_mobile_count=self._on_mobile_count,
        )
        self._connector.start()

    def _on_room_ready(self, room_id: str, pin: str):
        self.after(0, lambda: self._room_label.configure(text=room_id))
        self.after(0, lambda: self._pin_label.configure(text=pin))

    def _on_key(self, action: str):
        press(action)

    def _on_connect(self):
        self.after(0, lambda: self._status_label.configure(
            text='狀態：● 已連線 Gateway', text_color='green'))

    def _on_mobile_count(self, count: int):
        self.after(0, lambda: self._clients_label.configure(
            text=f'已連線手機：{count} 台'))

    def _on_disconnect(self):
        self.after(0, lambda: self._status_label.configure(
            text='狀態：● 斷線，自動重連中...', text_color='red'))

    def _regenerate_pin(self):
        if self._connector:
            self._connector.disconnect()
        self._room_label.configure(text='----')
        self._pin_label.configure(text='----')
        self._start_connector()

    def _reconnect(self):
        if self._connector:
            pin = self._connector.pin
            self._connector.disconnect()
            self._start_connector(pin=pin)

    # ── Tray ────────────────────────────────────────────────────────────────

    def _on_close(self):
        self.withdraw()
        menu = pystray.Menu(
            pystray.MenuItem('顯示視窗', self._show_window, default=True),
            pystray.MenuItem('結束', self._quit),
        )
        self._tray = pystray.Icon(
            'PPT Remote', _make_tray_icon(), 'PPT Remote', menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _show_window(self, icon=None, item=None):
        if self._tray:
            self._tray.stop()
            self._tray = None
        self.after(0, self.deiconify)

    def _quit(self, icon=None, item=None):
        if self._tray:
            self._tray.stop()
        if self._connector:
            self._connector.disconnect()
        self.after(0, self.destroy)


if __name__ == '__main__':
    App().mainloop()
```

- [ ] **Step 2: Run the GUI App manually**

```bash
cd gui-app && python main.py
```

Verify:
- Window appears with "連線中..." status
- If gateway is not running, status stays orange (no crash)
- Closing the window hides it to the system tray
- Right-clicking the tray icon shows "顯示視窗" and "結束"
- Clicking "顯示視窗" brings the window back

- [ ] **Step 3: Commit**

```bash
git add gui-app/main.py
git commit -m "feat: GUI app window with system tray"
```

---

## Task 8: End-to-End Smoke Test + PyInstaller Packaging

**Files:**
- Create: `gui-app/ppt-remote.spec`

- [ ] **Step 1: Full E2E smoke test**

Open 3 terminals:

**Terminal 1 — Gateway:**
```bash
cd gateway && python server.py
```
Expected output: Flask-SocketIO running on `http://0.0.0.0:5000`

**Terminal 2 — GUI App:**
```bash
cd gui-app && python main.py
```
Expected: window opens, status turns green "● 已連線 Gateway", Room ID and PIN appear.

**Terminal 3 — Simulate mobile:**
Open `http://localhost:5000` in a browser, enter the Room ID and PIN shown in the GUI App window, click "連線".

Verify:
- Login succeeds, remote control screen appears
- Clicking "下一頁 ▶" presses the right arrow key on the computer
- Clicking "◀ 上一頁" presses the left arrow key
- Clicking "▶ 開始簡報" sends F5
- Clicking "■ 結束簡報" sends Escape
- Closing the Gateway terminal → mobile shows "主機已離線"

- [ ] **Step 2: Run all tests**

```bash
cd gateway && python -m pytest tests/ -v
cd gui-app  && python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3: Install PyInstaller**

```bash
pip install pyinstaller
```

- [ ] **Step 4: Build GUI App executable**

```bash
cd gui-app && pyinstaller --onefile --windowed --name ppt-remote main.py
```

Expected: `gui-app/dist/ppt-remote` (Linux/macOS) or `gui-app/dist/ppt-remote.exe` (Windows) created.

- [ ] **Step 5: Test the built executable**

```bash
# Linux/macOS:
./gui-app/dist/ppt-remote

# Windows:
gui-app\dist\ppt-remote.exe
```

Expected: window opens and connects to the Gateway (make sure Gateway is running first).

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: PyInstaller build verified, E2E tested"
```

---

## Deployment Notes

**Gateway on VPS:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run with nginx + SSL (recommended for production)
# nginx config: proxy_pass http://127.0.0.1:5000; proxy_http_version 1.1;
# Upgrade: proxy_set_header Upgrade $http_upgrade;
# proxy_set_header Connection "upgrade";

python server.py
```

**GUI App — set Gateway URL:**
```bash
# Set the environment variable before running
export PPT_REMOTE_GATEWAY=wss://yourserver.com  # Linux/macOS
set PPT_REMOTE_GATEWAY=wss://yourserver.com     # Windows CMD
```

**macOS — pyautogui Accessibility permission:**
System Settings → Privacy & Security → Accessibility → add the terminal or app.

**Linux Wayland:**
```bash
sudo apt install ydotool
sudo systemctl enable --now ydotool
```
