from __future__ import annotations
from qtpy.QtCore import Qt
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QShortcut
from enum import Enum
from typing import Callable, NewType, Union, Tuple, TYPE_CHECKING
import re

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

QtKey = NewType("QtKey", int)
QtModifier = NewType("QtModifier", int)
KeyCombo = Union[
    Tuple[QtKey], Tuple[QtModifier, QtKey], Tuple[QtModifier, QtModifier, QtKey]
]


class Key(Enum):
    # keys
    Tab = "tab"
    Backspace = "backspace"
    Delete = "delete"
    Left = "left"
    Up = "up"
    Right = "right"
    Down = "down"
    PageUp = "pageup"
    PageDown = "pagedown"
    F1 = "f1"
    F2 = "f2"
    F3 = "f3"
    F4 = "f4"
    F5 = "f5"
    F6 = "f6"
    F7 = "f7"
    F8 = "f8"
    F9 = "f9"
    F10 = "f10"
    F11 = "f11"
    F12 = "f12"
    Exclam = "!"
    Dollar = "$"
    Percent = "%"
    Ampersand = "&"
    Apostrophe = "'"
    ParenLeft = "("
    ParenRight = ")"
    Asterisk = "*"
    Plus = "+"
    Comma = ","
    Minus = "-"
    Period = "."
    Slash = "/"
    Colon = ":"
    Semicolon = ";"
    Less = "<"
    Equal = "="
    Greater = ">"
    Question = "?"
    At = "@"

    # alphabets
    A = "a"
    B = "b"
    C = "c"
    D = "d"
    E = "e"
    F = "f"
    G = "g"
    H = "h"
    I = "i"
    J = "j"
    K = "k"
    L = "l"
    M = "m"
    N = "n"
    O = "o"
    P = "p"
    Q = "q"
    R = "r"
    S = "s"
    T = "t"
    U = "u"
    V = "v"
    W = "w"
    X = "x"
    Y = "y"
    Z = "z"

    # numbers
    _0 = "0"
    _1 = "1"
    _2 = "2"
    _3 = "3"
    _4 = "4"
    _5 = "5"
    _6 = "6"
    _7 = "7"
    _8 = "8"
    _9 = "9"

    # modifiers
    Meta = "meta"
    Shift = "shift"
    Ctrl = "ctrl"
    Alt = "alt"

    @classmethod
    def to_qtkey(cls, key: str | int | Key) -> QtKey:
        if isinstance(key, str):
            key = cls(key.lower())
        elif isinstance(key, int):
            key = str(key)
        elif isinstance(key, cls):
            pass
        else:
            raise TypeError(f"Unsupported type for a key: {type(key)}.")
        return getattr(Qt, f"Key_{key.name.lstrip('_')}")

    @classmethod
    def to_qtmodifier(cls, key: str | Key) -> QtModifier:
        if key == "control":
            key = cls.Ctrl
        elif isinstance(key, str):
            key = cls(key.lower())
        elif isinstance(key, cls):
            pass
        else:
            raise TypeError(f"Unsupported type for a modifier: {type(key)}.")
        return getattr(Qt, key.name.upper())

    # Add method enables expressions like ``Key.Ctrl + Key.A``.
    def __add__(self, other: str | Key) -> tuple[Key, Key]:
        cls = self.__class__
        if isinstance(other, str):
            other = cls(other.lower())
        elif not isinstance(other, cls):
            raise TypeError(f"Cannot add type {type(other)} to Key object.")
        return (self, other)

    def __radd__(self, other: str | Key | tuple[str | Key, ...]) -> tuple[Key, ...]:
        cls = self.__class__
        if isinstance(other, str):
            other = cls(other.lower())
            return (self, other)
        elif isinstance(other, cls):
            return (other, self)
        elif isinstance(other, tuple):
            return other + (self,)
        else:
            raise TypeError(f"Cannot add Key object to type {type(other)}.")


MODIFIERS = (Key.Meta, Key.Shift, Key.Ctrl, Key.Alt)


def ismodifier(s: str) -> bool:
    s = s.lower()
    if s == "control":
        return True
    else:
        return Key(s) in MODIFIERS


def parse_key_combo(key_combo: str) -> QtKey:
    # For compatibility with napari
    parsed = re.split("-(?=.+)", key_combo)
    return strs2keycombo(*parsed)


def strs2keycombo(*args: tuple[str | Key, ...]) -> KeyCombo:
    *modifiers, key = args
    if len(modifiers) > 2:
        raise ValueError("More than two modifiers found.")
    return tuple(Key.to_qtmodifier(m) for m in modifiers) + (Key.to_qtkey(key),)


def as_key_sequence(key_combo: tuple) -> QKeySequence:
    if not isinstance(key_combo, tuple):
        raise TypeError(f"Unsupported key combo: {key_combo!r}.")

    key0 = key_combo[0]
    if len(key_combo) == 1 and isinstance(key0, str) and not hasattr(Key, key0.lower()):
        qtkeycombo = parse_key_combo(*key_combo)
    else:
        qtkeycombo = strs2keycombo(*key_combo)
    return QKeySequence(sum(qtkeycombo))


def register_shortcut(keys, parent: QWidget, target: Callable):
    """Register a callback to a key-binding globally."""
    shortcut = QShortcut(as_key_sequence(keys), parent)
    shortcut.activated.connect(target)
    return None
