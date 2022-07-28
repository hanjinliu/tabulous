from __future__ import annotations
import re
from typing import (
    Any,
    Callable,
    Hashable,
    Iterator,
    Literal,
    MutableMapping,
    Sequence,
    TYPE_CHECKING,
    TypeVar,
    Union,
    overload,
)

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from functools import partial, reduce
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
    Ctrl | Shift: "Ctrl+Shift",
    Ctrl | Alt: "Ctrl+Alt",
    Alt | Shift: "Alt+Shift",
}


def _parse_string(keys: str):
    if keys in _MODIFIERS_INV.values():
        mods = keys.split("+")
        qtmod = reduce(or_, [_MODIFIERS[m] for m in mods])
        return qtmod, _NO_KEY

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


_NO_KEY = -1
_UNSET = object()


def _DUMMY_CALLBACK(*args):
    """Dummy callback function."""


KeyType = Union[QtGui.QKeyEvent, "QtKeys", str]


class QtKeys:
    """A custom class for handling key events."""

    def __init__(self, e: KeyType):
        if isinstance(e, QtGui.QKeyEvent):
            self.modifier = e.modifiers()
            self.key = e.key()
            if self.key > 10000:  # modifier only
                self.key = -1
        elif isinstance(e, str):
            mod, key = _parse_string(e)
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
        keystr = self.key_string()
        if mod == "None":
            return keystr
        elif keystr == "":
            return mod
        return "+".join([mod, keystr])

    def __repr__(self):
        return f"QtKeys({str(self)})"

    def __eq__(self, other):
        if isinstance(other, QtKeys):
            return self.modifier == other.modifier and self.key == other.key
        elif isinstance(other, str):
            qtmod, qtkey = _parse_string(other)
            return self.modifier == qtmod and self.key == qtkey
        else:
            raise TypeError("QtKeys can only be compared to QtKeys or str")

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
        if self.key == -1:
            return ""
        return QtGui.QKeySequence(self.key).toString()

    def has_ctrl(self) -> bool:
        """True if Ctrl is pressed."""
        return self.modifier & Qt.KeyboardModifier.ControlModifier

    def has_shift(self) -> bool:
        """True if Shift is pressed."""
        return self.modifier & Qt.KeyboardModifier.ShiftModifier

    def has_alt(self) -> bool:
        """True if Alt is pressed."""
        return self.modifier & Qt.KeyboardModifier.AltModifier


_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")


class RecursiveMapping(MutableMapping[_K, _V]):
    if TYPE_CHECKING:
        from abc import abstractmethod

        @abstractmethod
        def __getitem__(self, key: _K) -> _V | Self[_K, _V]:
            ...

        def get(self, key: _K, default: _V) -> _V | Self[_K, _V]:
            ...

        @abstractmethod
        def __iter__(self) -> Iterator[_V | Self[_K, _V]]:
            ...

        @abstractmethod
        def items(self) -> Iterator[tuple[_K, _V | Self[_K, _V]]]:
            ...


_F = TypeVar("_F", bound=Callable)


def _normalize_key_combo(s):
    if not isinstance(s, str):
        return s
    s = s.replace(" ", "")  # delete space
    if re.match(".+(,.+)+", s):
        # "Ctrl+A,Ctrl+C" matches, "Ctrl+," doesn't
        return s.split(",")
    return s


class QtKeyMap(RecursiveMapping[QtKeys, Callable]):
    """A mapping object for key map and key combo registration."""

    def __init__(
        self,
        instance: Any | None = None,
        activated: Callable = _DUMMY_CALLBACK,
        deactivated: Callable = _DUMMY_CALLBACK,
    ):
        self._keymap: dict[QtKeys, QtKeyMap | Callable] = {}
        self._current_map = None
        self._activated_callback = activated
        self._deactivated_callback = deactivated
        self._instances: dict[int, QtKeyMap] = {}
        self._obj = instance

    @property
    def current_map(self) -> Self:
        if self._current_map is None:
            return self
        return self._current_map

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        _id = id(obj)
        if (new := self._instances.get(_id, None)) is None:
            new = self.copy()
            new._obj = obj
            self._instances[_id] = new
        return new

    def copy(self) -> Self:
        new = self.__class__(
            self._obj, self._activated_callback, self._deactivated_callback
        )
        new._keymap = self._keymap.copy()
        return new

    def __getitem__(self, key: KeyType):
        return self._keymap[QtKeys(key)]

    def _get_active_item(self, key: KeyType):
        return self.current_map[QtKeys(key)]

    def _repr(self, indent: int = 0) -> str:
        indent_str = " " * indent
        strings = []
        if self._activated_callback is not _DUMMY_CALLBACK:
            strings.append(f"<activated>: {self._activated_callback!r}")
        if self._deactivated_callback is not _DUMMY_CALLBACK:
            strings.append(f"<deactivated>: {self._deactivated_callback!r}")
        for k, v in self.items():
            if isinstance(v, QtKeyMap):
                vrepr = v._repr(indent + 2)
            else:
                vrepr = repr(v)
            strings.append(f"{k}: {vrepr}")
        strings = f",\n{indent_str}  ".join(strings)
        return f"QtKeyMap(\n{indent_str}  {strings}\n{indent_str})"

    def __repr__(self) -> str:
        return self._repr()

    def add_child(self, key: KeyType, child_callback: Callable | None = None) -> None:
        kmap = QtKeyMap()
        if child_callback is not None:
            kmap.set_activated_callback(child_callback)
        self[key] = kmap
        return None

    @overload
    def bind(
        self,
        key: KeyType | Sequence[KeyType],
        callback: Literal[None] = None,
        overwrite: bool = False,
        **kwargs,
    ) -> Callable[[_F], _F]:
        ...

    @overload
    def bind(
        self,
        key: KeyType | Sequence[KeyType],
        callback: _F,
        overwrite: bool = False,
        **kwargs,
    ) -> _F:
        ...

    def bind(self, key, callback=None, overwrite=False, **kwargs) -> None:
        """Assign key or key combo to callback."""

        def wrapper(func):
            _func = _safe_partial(func, **kwargs)
            _key = _normalize_key_combo(key)

            if isinstance(_key, (str, QtKeys)):
                self._bind_key(_key, _func, overwrite)
            elif isinstance(_key, Sequence):
                self._bind_keycombo(_key, _func, overwrite)
            else:
                raise TypeError("key must be a string or a sequence of strings")
            return func

        return wrapper if callback is None else wrapper(callback)

    @overload
    def bind_deactivated(
        self,
        key: KeyType | Sequence[KeyType],
        callback: Literal[None] = None,
        overwrite: bool = False,
        **kwargs,
    ) -> Callable[[_F], _F]:
        ...

    @overload
    def bind_deactivated(
        self,
        key: KeyType | Sequence[KeyType],
        callback: _F,
        overwrite: bool = False,
        **kwargs,
    ) -> _F:
        ...

    def bind_deactivated(self, key, callback=None, overwrite=False, **kwargs):
        def wrapper(func):
            _func = _safe_partial(func, **kwargs)
            _key = _normalize_key_combo(key)

            if isinstance(_key, (str, QtKeys)):
                _key = [_key]
            current = self
            for i, k in enumerate(_key):
                if not isinstance(current, QtKeyMap):
                    seq = _key[:i]
                    raise ValueError(
                        f"Non keymap object {type(current)} encountered at {', '.join(seq)}."
                    )
                k = QtKeys(k)
                try:
                    current = current[k]
                except KeyError:
                    raise KeyError(f"Key {k} not found in {current!r}")
            current._deactivated_callback = _func
            return func

        return wrapper if callback is None else wrapper(callback)

    def rebind(
        self,
        old: KeyType | Sequence[KeyType],
        new: KeyType | Sequence[KeyType],
        overwrite: bool = False,
    ):
        old = _normalize_key_combo(old)
        new = _normalize_key_combo(new)
        if isinstance(old, (str, QtKeys, QtGui.QKeyEvent)):
            old = [old]
        if isinstance(new, (str, QtKeys, QtGui.QKeyEvent)):
            new = [new]
        src = self
        for k in old[:-1]:
            src = src[QtKeys(k)]
        self.bind(new, src.pop(old[-1]), overwrite=overwrite)
        return None

    def _bind_key(
        self, key: KeyType, callback: Callable, overwrite: bool = False
    ) -> None:
        if key in self and not overwrite:
            raise KeyError(f"Key {key} already exists")
        self[key] = callback
        return None

    def _bind_keycombo(
        self, combo: Sequence[KeyType], callback: Callable, overwrite: bool = False
    ) -> None:
        if isinstance(combo, str):
            raise TypeError("Combo must be an iterable of keys")
        current = self
        *pref, last = combo
        for key in pref:
            key = QtKeys(key)
            if key not in current:
                current.add_child(key)

            child = current[key]
            if callable(child):
                child = self.__class__(self._obj, activated=child)
                current[key] = child
            current = child

        current._bind_key(last, callback, overwrite)
        return None

    def get_or_activate(self, key: KeyType, default=_UNSET) -> Callable | Self:
        """Go to a new state."""
        key = QtKeys(key)
        try:
            current = self.current_map
            val = current[key]
            if isinstance(val, QtKeyMap):
                val._obj = self._obj
                self.activate(key)
            else:
                current.deactivate()

        except KeyError as e:
            if default is _UNSET:
                raise e
            val = default
        return val

    def set_activated_callback(self, callback: Callable):
        if not callable(callback):
            raise TypeError("Activated callback must be callable")
        self._activated_callback = callback

    def set_deactivated_callback(self, callback: Callable):
        if not callable(callback):
            raise TypeError("Activated callback must be callable")
        self._deactivated_callback = callback

    def press_key(self, key: KeyType) -> bool:
        """
        Emulate pressing a key.

        Parameters
        ----------
        key : KeyType
            Key expression to press.

        Returns
        -------
        bool
            True if the key triggered anything, False otherwise.
        """
        key = _normalize_key_combo(key)
        if isinstance(key, (str, QtKeys, QtGui.QKeyEvent)):
            return self._press_one_key(QtKeys(key))
        else:
            for k in key:
                out = self._press_one_key(QtKeys(k))
            return out

    def _press_one_key(self, key: QtKeys) -> bool:
        current = self.current_map
        try:
            callback = current[key]
        except KeyError:
            current.deactivate()
            self._current_map = None
            return False

        if isinstance(callback, QtKeyMap):
            callback._obj = self._obj
            self.activate(key)
        else:
            current.deactivate()
            self._current_map = None
            if self._obj is None:
                callback()
            else:
                callback(self._obj)
        return True

    def activate(self, key: KeyType) -> None:
        """Activate key combo trigger."""
        key = QtKeys(key)

        old = self.current_map
        current = self._get_active_item(key)
        if not isinstance(current, QtKeyMap):
            self._current_map = None
            raise KeyError(f"Key {key} is not a child")
        self._current_map = current
        if current._obj is None:
            current._activated_callback()
        else:
            current._activated_callback(current._obj)
        old.deactivate()
        return None

    def deactivate(self) -> None:
        """Deactivate key combo trigger."""
        if self._obj is None:
            self._deactivated_callback()
        else:
            self._deactivated_callback(self._obj)
        return None

    def __setitem__(self, key, value):
        if not isinstance(value, (QtKeyMap, Callable)):
            raise TypeError("Values in QtKeyMap must be QtKeyMap or callable.")
        self._keymap[QtKeys(key)] = value

    def __delitem__(self, key):
        del self._keymap[QtKeys(key)]

    def __iter__(self):
        return iter(self._keymap)

    def __len__(self):
        return len(self._keymap)


def _safe_partial(func, **kwargs):
    if kwargs:
        # check keyword arguments to avoid runtime error
        import inspect

        sig = inspect.signature(func)
        for name in kwargs:
            if name not in sig.parameters:
                raise TypeError(f"{func} does not accept keyword argument {name!r}.")
        return partial(func, **kwargs)
    return func
