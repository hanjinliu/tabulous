from tabulous._qt._keymap import QtKeyMap
from unittest.mock import MagicMock
import pytest

@pytest.mark.parametrize(
    "key",
    ["Ctrl+C", ["Ctrl+C", "C"], ["Ctrl+C", "Shift+Z", "Alt+O"], "Ctrl+C, Shift+Z, Alt+O"],
)
def test_keypress(key):
    mock = MagicMock()

    keymap = QtKeyMap()
    keymap.bind(key, mock)

    mock.assert_not_called()
    keymap.press_key("Ctrl+@")
    mock.assert_not_called()
    keymap.press_key(key)
    mock.assert_called_once()


def test_keycombo_initialization():
    mock = MagicMock()

    keymap = QtKeyMap()
    keymap.bind(["A", "B", "C"], mock)

    mock.assert_not_called()
    keymap.press_key("A")
    mock.assert_not_called()
    keymap.press_key("B")
    mock.assert_not_called()
    keymap.press_key("C")
    mock.assert_called_once()
    mock.reset_mock()
    keymap.press_key("C")  # combo initialized
    mock.assert_not_called()
    keymap.press_key("A")
    keymap.press_key("B")
    keymap.press_key("B")
    keymap.press_key("C")
    mock.assert_not_called()
    keymap.press_key("A")
    keymap.press_key("B")
    keymap.press_key("C")
    mock.assert_called_once()


def test_activated_callback():
    keymap = QtKeyMap()
    mock = MagicMock()

    keymap.bind(["Ctrl+C", "Ctrl+V"], lambda: 0)
    keymap["Ctrl+C"].set_activated_callback(mock)
    keymap.press_key("Ctrl+C")
    mock.assert_called_once()

def test_callback_to_child_map():
    keymap = QtKeyMap()
    mock = MagicMock()

    func0 = lambda: mock(0)
    func1 = lambda: mock(1)
    keymap.bind("Ctrl+C", func0)
    keymap.bind(["Ctrl+C", "Ctrl+V"], func1)
    keymap.press_key("Ctrl+C")
    mock.assert_called_once()
    mock.assert_called_with(0)
    keymap.press_key("Ctrl+V")
    mock.assert_called_with(1)

@pytest.mark.parametrize("key0", ["Ctrl+C", "Ctrl+K, Ctrl+C"])
@pytest.mark.parametrize("key1", ["Ctrl+A", "Ctrl+K, Ctrl+A"])
def test_rebind(key0, key1):
    keymap = QtKeyMap()
    mock = MagicMock()

    keymap.bind(key0, mock)
    keymap.rebind(key0, key1)

    keymap.press_key(key0)
    mock.assert_not_called()

    keymap.press_key(key1)
    mock.assert_called_once()
