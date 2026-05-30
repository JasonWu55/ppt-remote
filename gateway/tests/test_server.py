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
