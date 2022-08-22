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
    keymap.bind("Ctrl+C", mock)
    keymap.press_key("Ctrl+C")
    mock.assert_called_once()

def test_activate_modifier_only():
    keymap = QtKeyMap()
    mock1 = MagicMock()
    mock2 = MagicMock()

    keymap.bind(["Alt"], mock1)
    keymap.bind(["Alt", "A"], mock2)

    keymap.press_key("Alt")
    mock1.assert_called_once()
    mock1.reset_mock()

    keymap.press_key("A")
    mock2.assert_called_once()

    keymap.press_key("Alt")
    mock1.assert_called_once()
    mock1.reset_mock()

    # BUG: this is not working
    # keymap.press_key("Alt")
    # mock1.assert_not_called()

    # keymap.press_key("Alt")
    # mock1.assert_called_once()

# def test_combo_with_conflicted_modifier():
#     """In Qt, Alt is activated before Alt+A is activated."""

#     keymap = QtKeyMap()
#     mock1 = MagicMock()
#     mock2 = MagicMock()

#     keymap.bind(["Alt"], mock1)
#     keymap.bind(["Alt", "A"], mock2)

#     keymap.press_key("Alt")
#     mock1.assert_called_once()

#     keymap.press_key("Alt+A")
#     mock2.assert_called_once()

def test_combo_with_different_modifiers():
    keymap = QtKeyMap()
    mock = MagicMock()

    keymap.bind("Ctrl+K, Shift+A", mock)

    keymap.press_key("Ctrl+K")
    keymap.press_key("Shift+A")
    mock.assert_called_once()
    mock.reset_mock()

    keymap.press_key("Shift+A")
    mock.assert_not_called()

def test_deactivated_callback():
    keymap = QtKeyMap()
    mock = MagicMock()

    keymap.bind(["Ctrl+C", "Ctrl+V"], lambda: 0)
    keymap.bind_deactivated("Ctrl+C", mock)
    keymap.press_key("Ctrl+C")
    mock.assert_not_called()
    keymap.press_key("Ctrl+V")
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

def test_parametric():
    keymap = QtKeyMap()
    mock = MagicMock()

    keymap.bind("Ctrl+{}", mock)
    keymap.bind("Ctrl+A", lambda: None)
    keymap.bind("Ctrl+B, Ctrl+C", lambda: None)

    mock.assert_not_called()
    keymap.press_key("Ctrl+A")
    mock.assert_not_called()
    keymap.press_key("Ctrl+2")
    mock.assert_called_with("2")
    keymap.press_key("Ctrl+Z")
    mock.assert_called_with("Z")
    mock.reset_mock()
    keymap.press_key("Ctrl+Shift+1")
    mock.assert_not_called()
    keymap.press_key("Ctrl")
    mock.assert_not_called()
    keymap.press_key("Ctrl+T")
    mock.assert_called_with("T")
    mock.reset_mock()
    keymap.press_key("Ctrl+B")
    mock.assert_not_called()

def test_parametric_combo():
    keymap = QtKeyMap()
    mock = MagicMock()

    keymap.bind("Ctrl+B, Alt+{}", mock)

    keymap.press_key("Ctrl+B")
    mock.assert_not_called()
    keymap.press_key("Alt+A")
    mock.assert_called_with("A")
