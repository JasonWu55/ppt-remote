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
