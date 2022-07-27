from __future__ import annotations
from abc import abstractmethod
from typing import (
    Callable,
    Hashable,
    Iterator,
    MutableMapping,
    Sequence,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from functools import reduce
from operator import or_

if TYPE_CHECKING:
    from typing_extensions import Self

NoModifier = Qt.KeyboardModifier.NoModifier
Ctrl = Qt.KeyboardModifier.ControlModifier
Shift = Qt.KeyboardModifier.ShiftModifier
Alt = Qt.KeyboardModifier.AltModifier
Meta = Qt.KeyboardModifier.MetaModifier

_MODIFIERS = {
    "None": NoModifier,
    "Shift": Shift,
    "Ctrl": Ctrl,
    "Control": Ctrl,
    "Alt": Alt,
    "Meta": Meta,
}

_SYMBOLS = {
    "!": "Exclam",
    '"': "QuoteDbl",
    "#": "NumberSign",
    "$": "Dollar",
    "%": "Percent",
    "&": "Ampersand",
    "'": "Apostrophe",
    "(": "ParenLeft",
    ")": "ParenRight",
    "*": "Asterisk",
    "+": "Plus",
    ",": "Comma",
    "-": "Minus",
    ".": "Period",
    "/": "Slash",
    ":": "Colon",
    ";": "Semicolon",
    "<": "Less",
    "=": "Equal",
    ">": "Greater",
    "?": "Question",
    "@": "At",
    "[": "BracketLeft",
    "\\": "Backslash",
    "]": "BracketRight",
    "^": "AsciiCircum",
    "_": "Underscore",
    "`": "QuoteLeft",
    "{": "BraceLeft",
    "|": "Bar",
    "}": "BraceRight",
    "~": "AsciiTilde",
}

_MODIFIERS_INV = {
    NoModifier: "None",
    Shift: "Shift",
    Ctrl: "Ctrl",
    Alt: "Alt",
    Meta: "Meta",
    Ctrl & Shift: "Ctrl+Shift",
    Ctrl & Alt: "Ctrl+Alt",
    Alt & Shift: "Alt+Shift",
}


def _str_to_keys(keys: str):
    # if keys in _MODIFIERS:
    #     mods = _MODIFIERS[keys]
    #     btn =
    *mods, btn = keys.split("+")
    # get modifiler
    if not mods:
        qtmod = Qt.KeyboardModifier.NoModifier
    else:
        qtmod = reduce(or_, [_MODIFIERS[m] for m in mods])
    # get button
    if btn in _SYMBOLS:
        btn = _SYMBOLS[btn]
    qtkey = getattr(Qt.Key, f"Key_{btn}")
    return qtmod, qtkey


KeyType = Union[QtGui.QKeyEvent, "QtKeys", str]


class QtKeys:
    """A custom class for handling key events."""

    def __init__(self, e: KeyType):
        if isinstance(e, QtGui.QKeyEvent):
            self.modifier = e.modifiers()
            self.key = e.key()
        elif isinstance(e, str):
            mod, key = _str_to_keys(e)
            self.modifier = mod
            self.key = key
        elif isinstance(e, QtKeys):
            self.modifier = e.modifier
            self.key = e.key
        else:
            raise TypeError("QtKeys can only be initialized with QKeyEvent or QtKeys")

    def __hash__(self) -> int:
        return hash((self.modifier, self.key))

    def __str__(self) -> str:
        mod = _MODIFIERS_INV.get(self.modifier, "???")
        if mod == "None":
            return self.key_string()
        return "+".join([mod, self.key_string()])

    def __repr__(self):
        return f"QtKeys({str(self)})"

    def __eq__(self, other):
        if isinstance(other, QtKeys):
            return self.modifier == other.modifier and self.key == other.key
        elif isinstance(other, str):
            qtmod, qtkey = _str_to_keys(other)
            return self.modifier == qtmod and self.key == qtkey
        else:
            raise TypeError

    def is_typing(self) -> bool:
        """True if key is a letter or number."""
        return (
            self.modifier
            in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ShiftModifier,
            )
            and (Qt.Key.Key_Exclam <= self.key <= Qt.Key.Key_ydiaeresis)
        )

    def key_string(self) -> str:
        """Get clicked key in string form."""
        return QtGui.QKeySequence(self.key).toString()

    def has_ctrl(self) -> bool:
        """True if Ctrl is pressed."""
        return self.modifier & Qt.KeyboardModifier.ControlModifier

    def has_shift(self) -> bool:
        """True if Shift is pressed."""
        return self.modifier & Qt.KeyboardModifier.ShiftModifier


_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")


class RecursiveMapping(MutableMapping[_K, _V]):
    if TYPE_CHECKING:

        @abstractmethod
        def __getitem__(self, key: _K) -> _V | Self[_K, _V]:
            ...

        def get(self, key: _K, default: _V) -> _V | Self[_K, _V]:
            ...

        @abstractmethod
        def __iter__(self) -> Iterator[_V | Self[_K, _V]]:
            return super().__iter__()


class QtKeyMap(RecursiveMapping[QtKeys, Callable]):
    def __init__(self, key=None, parent: QtKeyMap | None = None):
        self._keymap = {}
        self._current_state = None
        self._parent = parent
        self._self_key = key

    def __getitem__(self, key: KeyType):
        key = QtKeys(key)
        if self._current_state is None:
            return self._keymap[key]

        return self._keymap[self._current_state][key]

    def _repr(self, indent: int = 0) -> str:
        indent_str = " " * indent
        strings = []
        for k, v in self._keymap.items():
            if isinstance(v, QtKeyMap):
                vrepr = v._repr(indent + 2)
            else:
                vrepr = repr(v)
            strings.append(f"{k}: {vrepr}")
        strings = f",\n{indent_str}  ".join(strings)
        return f"QtKeyMap(\n{indent_str}  {strings}\n{indent_str})"

    def __repr__(self) -> str:
        return self._repr()

    def add_child(self, key: KeyType) -> None:
        self[key] = QtKeyMap(key=QtKeys(key), parent=self)

    def add_callback(
        self, key: KeyType, callback: Callable, overwrite: bool = False
    ) -> None:
        if key in self._keymap and not overwrite:
            raise KeyError(f"Key {key} already exists")
        self[key] = callback

    def add_combo(
        self, combo: Sequence[KeyType], callback: Callable, overwrite: bool = False
    ) -> None:
        if isinstance(combo, str):
            raise TypeError("Combo must be an iterable of keys")
        current = self
        *pref, last = combo
        for key in pref:
            if key not in current._keymap:
                current.add_child(key)
            current = current[key]
        current.add_callback(last, callback, overwrite)

    def emit(self, key: KeyType) -> None:
        key = QtKeys(key)
        callback = self.get(key, None)
        if isinstance(callback, QtKeyMap):
            if self._current_state is None:
                self.activate(key)
            else:
                callback.activate(key)
            print("activated", key)
        else:
            self.deactivate_all()
            if callback is not None:
                callback()
        return None

    def activate(self, key: KeyType):
        key = QtKeys(key)
        child = self[key]
        if not isinstance(child, QtKeyMap):
            raise KeyError(f"Key {key} is not a child")
        self._current_state = key

    def deactivate(self):
        self._current_state = None

    def deactivate_all(self):
        current = self
        current.deactivate()
        while parent := current._parent:
            parent.deactivate()
            current = parent
        return None

    def __setitem__(self, key, value):
        self._keymap[QtKeys(key)] = value

    def __delitem__(self, key):
        del self._keymap[key]

    def __iter__(self):
        return iter(self._keymap)

    def __len__(self):
        return len(self._keymap)

    @property
    def ancestor(self) -> Self:
        current = self
        while parent := current._parent:
            current = parent
        return current
