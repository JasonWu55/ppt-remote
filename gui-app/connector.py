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
