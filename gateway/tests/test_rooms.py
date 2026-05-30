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
