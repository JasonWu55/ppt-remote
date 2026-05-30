import sys
from unittest.mock import MagicMock

import pytest

# Mock pyautogui before importing keyboard to avoid display connection issues
sys.modules['pyautogui'] = MagicMock()

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
