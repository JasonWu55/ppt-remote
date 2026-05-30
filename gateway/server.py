from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from rooms import RoomManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ppt-remote'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

room_manager = RoomManager()


def _get_client_ip() -> str:
    raw = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    if raw is None:
        return '127.0.0.1'
    return raw.split(',')[0].strip()


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
    role, room_id = entry
    if role == 'gui':
        result = room_manager.remove_gui(request.sid)
        if result:
            removed_room_id, mobile_sids = result
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
