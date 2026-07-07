import secrets
import string
import threading
from datetime import datetime, timedelta

MAX_FAILURES = 10
BLOCK_SECONDS = 60
ROOM_ID_LEN = 4
MAX_MOBILE_PER_ROOM = 10


class RoomManager:
    def __init__(self):
        self._rooms = {}        # room_id -> {pin, gui_sid, mobile_sids}
        self._client_role = {}  # sid -> (role, room_id)
        self._ip_failures = {}  # ip -> {count, blocked_until, last_failure}
        # ponytail: single coarse lock is deliberate — state is tiny and every
        # critical section is sub-microsecond; finer-grained locking would add
        # complexity/deadlock risk with no measurable benefit.
        self._lock = threading.Lock()

    def create_room(self, gui_sid: str, pin: str) -> str:
        with self._lock:
            room_id = self._gen_room_id()
            self._rooms[room_id] = {'pin': pin, 'gui_sid': gui_sid, 'mobile_sids': set()}
            self._client_role[gui_sid] = ('gui', room_id)
            return room_id

    def join_room(self, room_id: str, pin: str, mobile_sid: str, ip: str) -> tuple[bool, str | None]:
        with self._lock:
            if self._is_blocked(ip):
                return False, 'blocked'
            if room_id not in self._rooms or self._rooms[room_id]['pin'] != pin:
                self._record_failure(ip)
                return False, 'invalid'
            if len(self._rooms[room_id]['mobile_sids']) >= MAX_MOBILE_PER_ROOM:
                return False, 'room_full'
            self._rooms[room_id]['mobile_sids'].add(mobile_sid)
            self._client_role[mobile_sid] = ('mobile', room_id)
            return True, None

    def get_gui_sid(self, room_id: str) -> str | None:
        with self._lock:
            return self._rooms.get(room_id, {}).get('gui_sid')

    def get_mobile_sids(self, room_id: str) -> set[str]:
        with self._lock:
            return set(self._rooms.get(room_id, {}).get('mobile_sids', set()))

    def remove_gui(self, gui_sid: str) -> tuple[str, set] | None:
        with self._lock:
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

    def remove_mobile(self, mobile_sid: str) -> None:
        with self._lock:
            entry = self._client_role.pop(mobile_sid, None)
            if entry is None:
                return
            _, room_id = entry
            if room_id in self._rooms:
                self._rooms[room_id]['mobile_sids'].discard(mobile_sid)

    def get_role(self, sid: str):
        with self._lock:
            entry = self._client_role.get(sid)
            if entry is None:
                return None
            role, room_id = entry
            return role, room_id

    def _gen_room_id(self) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            room_id = ''.join(secrets.choice(chars) for _ in range(ROOM_ID_LEN))
            if room_id not in self._rooms:
                return room_id

    def _is_blocked(self, ip: str) -> bool:
        entry = self._ip_failures.get(ip)
        if not entry:
            return False
        now = datetime.now()
        blocked_until = entry.get('blocked_until')
        if blocked_until and now < blocked_until:
            return True
        # Block expired or failure window passed: forget old failures.
        if blocked_until or now - entry['last_failure'] >= timedelta(seconds=BLOCK_SECONDS):
            del self._ip_failures[ip]
        return False

    def _record_failure(self, ip: str):
        now = datetime.now()
        window = timedelta(seconds=BLOCK_SECONDS)
        # Opportunistically prune entries whose failure window has passed
        # (an expired block also implies an expired window), so the dict
        # cannot grow without bound and stale counts reset.
        stale = [k for k, e in self._ip_failures.items()
                 if now - e['last_failure'] >= window]
        for k in stale:
            del self._ip_failures[k]
        entry = self._ip_failures.setdefault(
            ip, {'count': 0, 'blocked_until': None, 'last_failure': now})
        entry['count'] += 1
        entry['last_failure'] = now
        if entry['count'] >= MAX_FAILURES:
            entry['blocked_until'] = now + window
