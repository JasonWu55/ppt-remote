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


def test_run_retries_initial_connect_until_disconnect(
        mock_sio, conn, callbacks, mocker):
    mocker.patch.object(conn._stopped, 'wait')  # skip backoff sleeps

    def fail(url):
        if mock_sio.connect.call_count >= 3:
            conn.disconnect()
        raise RuntimeError('gateway down')

    mock_sio.connect.side_effect = fail
    conn._run()
    assert mock_sio.connect.call_count == 3
    # third failure happens after disconnect() — no stale UI callback
    assert callbacks['on_disconnect'].call_count == 2


def test_run_signals_on_disconnect_when_initial_connect_fails(
        mock_sio, conn, callbacks, mocker):
    mocker.patch.object(conn._stopped, 'wait')
    mock_sio.connect.side_effect = [RuntimeError('gateway down'), None]
    conn._run()
    callbacks['on_disconnect'].assert_called_once()
    assert mock_sio.connect.call_count == 2
    mock_sio.wait.assert_called_once()


def test_run_does_not_retry_after_disconnect(mock_sio, conn):
    conn.disconnect()
    conn._run()
    mock_sio.connect.assert_not_called()


def test_run_stops_after_successful_connect_and_wait(mock_sio, conn):
    conn._run()
    mock_sio.connect.assert_called_once()
    mock_sio.wait.assert_called_once()


def test_run_disconnects_if_stopped_during_connect(mock_sio, conn):
    # disconnect() lands while connect() is in flight: the socketio client's
    # disconnect is a no-op then, so _run must tear down and never wait()
    mock_sio.connect.side_effect = lambda url: conn.disconnect()
    conn._run()
    mock_sio.wait.assert_not_called()
    assert mock_sio.disconnect.call_count == 2  # once in disconnect(), once in _run
