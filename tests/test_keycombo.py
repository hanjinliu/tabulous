from tabulous._qt._keymap import QtKeyMap
from unittest.mock import MagicMock
import pytest

@pytest.mark.parametrize(
    "key",
    ["Ctrl+C", ["Ctrl+C", "C"], ["Ctrl+C", "Shift+Z", "Alt+O"]],
)
def test_keypress(key):
    mock = MagicMock()

    keymap = QtKeyMap()
    keymap.bind(key, mock)

    mock.assert_not_called()
    keymap.press_key("Ctrl+@")
    mock.assert_not_called()
    if isinstance(key, str):
        keymap.press_key(key)
    else:
        [keymap.press_key(k) for k in key]
    mock.assert_called_once()
