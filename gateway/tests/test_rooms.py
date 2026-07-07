import threading

import pytest
from datetime import datetime, timedelta
from rooms import RoomManager, BLOCK_SECONDS

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

def test_failure_count_resets_after_window(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    for _ in range(9):
        rm.join_room(room_id=room_id, pin='wrong',
                     mobile_sid='mob-x', ip='5.6.7.8')
    # Age the failures past the window
    rm._ip_failures['5.6.7.8']['last_failure'] = (
        datetime.now() - timedelta(seconds=BLOCK_SECONDS + 1)
    )
    # A new failure must not trigger a block: the stale count was reset
    success, reason = rm.join_room(room_id=room_id, pin='wrong',
                                   mobile_sid='mob-x', ip='5.6.7.8')
    assert success is False
    assert reason == 'invalid'
    assert rm._ip_failures['5.6.7.8']['count'] == 1
    # And a valid join still works
    success, reason = rm.join_room(room_id=room_id, pin='1234',
                                   mobile_sid='mob-1', ip='5.6.7.8')
    assert success is True

def test_expired_failure_entries_are_pruned(rm):
    room_id = rm.create_room(gui_sid='gui-1', pin='1234')
    rm.join_room(room_id, 'wrong', 'mob-x', '9.9.9.9')
    # Age the entry past the window
    rm._ip_failures['9.9.9.9']['last_failure'] = (
        datetime.now() - timedelta(seconds=BLOCK_SECONDS + 1)
    )
    # A failure from a different IP prunes the expired entry
    rm.join_room(room_id, 'wrong', 'mob-y', '8.8.8.8')
    assert '9.9.9.9' not in rm._ip_failures
    assert set(rm._ip_failures) == {'8.8.8.8'}

def test_concurrent_room_operations(rm):
    errors = []

    def worker(n):
        try:
            for i in range(50):
                gui_sid = f'gui-{n}-{i}'
                mob_sid = f'mob-{n}-{i}'
                room_id = rm.create_room(gui_sid=gui_sid, pin='1234')
                success, reason = rm.join_room(room_id, '1234', mob_sid,
                                               f'10.0.{n}.{i}')
                assert success is True, reason
                assert rm.get_gui_sid(room_id) == gui_sid
                assert mob_sid in rm.get_mobile_sids(room_id)
                rm.remove_mobile(mob_sid)
                result = rm.remove_gui(gui_sid)
                assert result is not None and result[0] == room_id
        except Exception as exc:  # pragma: no cover - only on failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    # Everything was cleaned up: no leaked rooms or role mappings
    assert rm._rooms == {}
    assert rm._client_role == {}

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
