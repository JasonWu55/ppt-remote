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
