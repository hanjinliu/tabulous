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

from qtpy import QtGui
from qtpy.QtCore import Qt
from functools import reduce
from operator import or_

from tabulous.exceptions import TriggerParent

from ._callback import BoundCallback

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
    "Esc": "Escape",
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
        return qtmod, ExtKey.No

    *mods, btn = keys.split("+")

    # get modifiler
    if not mods:
        qtmod = Qt.KeyboardModifier.NoModifier
    else:
        qtmod = reduce(or_, [_MODIFIERS[m] for m in mods])

    # get button
    if btn in _SYMBOLS:
        btn = _SYMBOLS[btn]

    if btn != "{}":
        qtkey = getattr(Qt.Key, f"Key_{btn}")
    else:
        qtkey = ExtKey.Any
    return qtmod, qtkey


def _parse_modifiers(km: Qt.KeyboardModifiers) -> Qt.KeyboardModifiers:
    """Keypad modifier should be ignored."""
    if km & Qt.KeyboardModifier.KeypadModifier:
        km ^= Qt.KeyboardModifier.KeypadModifier

    return km


class ExtKey:
    """Key extension."""

    No = -1
    Any = -2


KeyType = Union[QtGui.QKeyEvent, "QtKeys", str]
MODIFIER_KEYS = frozenset(
    {Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Meta, Qt.Key.Key_Alt}
)
ARROW_KEYS = frozenset(
    {Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right}
)
FUNC_ARROW_KEYS = frozenset(
    {Qt.Key.Key_Home, Qt.Key.Key_End, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown}
)


class QtKeys:
    """A custom class for handling key events."""

    def __init__(self, e: KeyType):
        if isinstance(e, QtGui.QKeyEvent):
            self.modifier = _parse_modifiers(e.modifiers())
            self.key = e.key()
            if self.key in MODIFIER_KEYS:  # modifier only
                self.key = ExtKey.No
        elif isinstance(e, str):
            mod, key = _parse_string(e)
            self.modifier = mod
            self.key = key
        elif isinstance(e, QtKeys):
            self.modifier = e.modifier
            self.key = e.key
        else:
            raise TypeError(
                "QtKeys can only be initialized with QKeyEvent, str or QtKeys, "
                f"but got {type(e)}."
            )

    def __hash__(self) -> int:
        return hash((self.modifier, self.key))

    def _reduce_key(self) -> Self:
        if self.key == ExtKey.No:
            # this case is needed to avoid triggering parametric key binding with
            # modifiers.
            return self
        new = QtKeys(self)
        new.key = ExtKey.Any
        return new

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
        return self.modifier in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.ShiftModifier,
        ) and (Qt.Key.Key_Exclam <= self.key <= Qt.Key.Key_ydiaeresis)

    def is_moving(self) -> bool:
        """True if arrows are pushed."""
        return self.key in ARROW_KEYS

    def is_moving_func(self) -> bool:
        """True if function arrows are pushed."""
        return self.key in FUNC_ARROW_KEYS

    def key_string(self, check_shift: bool = False) -> str:
        """Get clicked key in string form."""
        if self.key == -1:
            return ""
        elif self.key == -2:
            return "{}"

        s = QtGui.QKeySequence(self.key).toString()
        if check_shift and not self.has_shift():
            s = s.lower()
        return s

    def has_ctrl(self) -> bool:
        """True if Ctrl is pressed."""
        return bool(self.modifier & Qt.KeyboardModifier.ControlModifier)

    def has_shift(self) -> bool:
        """True if Shift is pressed."""
        return bool(self.modifier & Qt.KeyboardModifier.ShiftModifier)

    def has_alt(self) -> bool:
        """True if Alt is pressed."""
        return bool(self.modifier & Qt.KeyboardModifier.AltModifier)

    def has_key(self) -> bool:
        """True if non-modifier key is pressed."""
        return self.key != ExtKey.No


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


def _normalize_key_combo(s: list[str] | str) -> list[str] | str:
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
        activated: Callable | None = None,
        deactivated: Callable | None = None,
    ):
        self._keymap: dict[QtKeys, QtKeyMap | Callable] = {}
        self._current_map: QtKeyMap | None = None
        self._current_combo: list[QtKeys] = []
        self._activated_callback = activated or _DUMMY_CALLBACK
        self._deactivated_callback = deactivated or _DUMMY_CALLBACK
        self._released_callback = _DUMMY_CALLBACK
        self._instances: dict[int, QtKeyMap] = {}
        self._obj = instance

    @property
    def current_map(self) -> Self:
        """Return the current active keymap object."""
        if self._current_map is None:
            return self
        return self._current_map

    @property
    def previous_map(self) -> Self | None:
        """Return the parent of the current active keymap object."""
        if len(self._current_combo) == 0:
            return None
        current = self
        for k in self._current_combo[:-1]:
            current = current._keymap[k]
        return current

    @property
    def activated_callback(self) -> BoundCallback | None:
        """The function to be called when the keymap is activated."""
        if (a := self._activated_callback) is not _DUMMY_CALLBACK:
            return a
        return None

    @property
    def deactivated_callback(self) -> BoundCallback | None:
        """The function to be called when the keymap is deactivated."""
        if (a := self._deactivated_callback) is not _DUMMY_CALLBACK:
            return a
        return None

    @property
    def last_pressed(self) -> QtKeys | None:
        """The last pressed key."""
        if self._current_combo:
            return self._current_combo[-1]
        return None

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
        """Return a copy of an instance."""
        new = self.__class__(
            self._obj, self._activated_callback, self._deactivated_callback
        )
        new._keymap = self._keymap.copy()
        return new

    def __getitem__(self, key: KeyType):
        return self._keymap[QtKeys(key)]

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
        """Add a child keymap."""
        kmap = QtKeyMap()
        if child_callback is not None:
            kmap._activated_callback = BoundCallback(child_callback, keys=key)
        self[key] = kmap
        return None

    @overload
    def bind(
        self,
        key: KeyType | Sequence[KeyType],
        callback: Literal[None] = None,
        overwrite: bool = False,
        desc: str | None = None,
        **kwargs,
    ) -> Callable[[_F], _F]:
        ...

    @overload
    def bind(
        self,
        key: KeyType | Sequence[KeyType],
        callback: _F,
        overwrite: bool = False,
        desc: str | None = None,
        **kwargs,
    ) -> _F:
        ...

    def bind(self, key, callback=None, *, overwrite=False, desc=None, **kwargs):
        """Assign key or key combo to callback."""

        def wrapper(func):
            _key = _normalize_key_combo(key)
            _func = BoundCallback(func, keys=_key, desc=desc, kwargs=kwargs)

            if isinstance(_key, (str, QtKeys)):
                self._bind_key(_key, _func, overwrite)
            elif isinstance(_key, Sequence):
                self._bind_keycombo(_key, _func, overwrite)
            else:
                raise TypeError("key must be a string or a sequence of strings")
            return func

        return wrapper if callback is None else wrapper(callback)

    def unbind(self, key: str) -> None:
        _key = _normalize_key_combo(key)
        if isinstance(_key, (str, QtKeys)):
            del self._current_map[_key]
        elif isinstance(_key, Sequence):
            current = self
            *pref, last = _key
            for k in pref:
                current = current[k]
            del current[last]
        else:
            raise TypeError("key must be a string or a sequence of strings")
        return None

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
            _key = _normalize_key_combo(key)
            _func = BoundCallback(func, keys=_key, kwargs=kwargs)

            if isinstance(_key, (str, QtKeys)):
                _key = [_key]
            current = self
            for i, k in enumerate(_key):
                if not isinstance(current, QtKeyMap):
                    seq = _key[:i]
                    raise ValueError(
                        f"Non keymap object {type(current)} encountered at "
                        f"{', '.join(seq)}."
                    )
                k = QtKeys(k)
                try:
                    current = current[k]
                except KeyError:
                    raise KeyError(f"Key {k} not found in {current!r}")
            if current._deactivated_callback is not _DUMMY_CALLBACK and not overwrite:
                raise ValueError(f"Key {key} already exists")
            current._deactivated_callback = _func
            return func

        return wrapper if callback is None else wrapper(callback)

    def bind_released(self, key, callback=None, overwrite=False, desc=None, **kwargs):
        def wrapper(func):
            _key = _normalize_key_combo(key)
            _func = BoundCallback(func, keys=_key, kwargs=kwargs)

            if isinstance(_key, (str, QtKeys)):
                _key = [_key]
            current = self
            for i, k in enumerate(_key):
                if not isinstance(current, QtKeyMap):
                    seq = _key[:i]
                    raise ValueError(
                        f"Non keymap object {type(current)} encountered at "
                        f"{', '.join(seq)}."
                    )
                k = QtKeys(k)
                try:
                    current = current[k]
                except KeyError:
                    raise KeyError(f"Key {k} not found in {current!r}")
            if current._released_callback is not _DUMMY_CALLBACK and not overwrite:
                raise ValueError(f"Key {key} already exists")
            current._released_callback = _func
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
        self, key: KeyType, callback: BoundCallback, overwrite: bool = False
    ) -> None:
        child = self.get(key, None)
        if callable(child):
            if not overwrite:
                raise ValueError(f"A callback is already assigned to key {key}.")
            self[key] = callback

        elif isinstance(child, QtKeyMap):
            if not overwrite and child._activated_callback is not _DUMMY_CALLBACK:
                raise ValueError(
                    f"A keymap with callback is already assigned to key {key}."
                )
            child._activated_callback = callback

        else:
            self[key] = callback

        return None

    def _bind_keycombo(
        self, combo: Sequence[KeyType], callback: BoundCallback, overwrite: bool = False
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

    def release_key(self) -> None:
        current = self.current_map
        if current._obj is None:
            current._released_callback()
        else:
            current._released_callback(current._obj)
        return None

    def _press_one_key(self, key: QtKeys) -> bool:
        current = self.current_map
        _is_parametric = False
        try:
            callback = current[key]
        except KeyError:
            try:
                callback = current[key._reduce_key()]
            except KeyError:
                # Don't lose the combo if only a modifier is pressed
                last = self.last_pressed
                if key.key != ExtKey.No:
                    repress = self._current_map is not None
                    current.deactivate()
                    self.initialize()
                    if repress:
                        # if key combo is initialized half-way, repress the last key
                        return self._press_one_key(key)

                if last is not None and last.key == ExtKey.No and key.key != ExtKey.No:
                    return self._press_one_key(key)

                return False
            _is_parametric = True

        if isinstance(callback, QtKeyMap):
            callback._obj = self._obj
            try:
                self.activate(key)
            except TriggerParent:
                return False
        else:
            current.deactivate()
            self.initialize()
            if self._obj is not None:
                callback = callback.__get__(self._obj)
            try:
                if _is_parametric:
                    callback(key.key_string())
                else:
                    callback()
            except TriggerParent:
                return False

        last = self.last_pressed
        if last is not None and last.key == ExtKey.No and last.modifier == key.modifier:
            self._current_combo.pop()
        self._current_combo.append(key)
        return True

    def activate(self, key: KeyType) -> None:
        """Activate key combo trigger."""
        key = QtKeys(key)

        old = self.current_map
        current = self.current_map[key]
        if not isinstance(current, QtKeyMap):
            self.initialize()
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

    def initialize(self):
        self._current_map = None
        self._current_combo.clear()
        return None

    def to_widget(self):
        from ._keymapview import QtKeyMapView

        return QtKeyMapView.from_keymap(self)

    def __setitem__(self, key, value):
        if callable(value):
            value = BoundCallback(value)
        elif not isinstance(value, QtKeyMap):
            raise TypeError("Values in QtKeyMap must be QtKeyMap or callable.")
        self._keymap[QtKeys(key)] = value

    def __delitem__(self, key):
        del self._keymap[QtKeys(key)]

    def __iter__(self):
        return iter(self._keymap)

    def __len__(self):
        return len(self._keymap)


def _DUMMY_CALLBACK(*args):
    """Dummy callback function."""


_DUMMY_CALLBACK = BoundCallback(_DUMMY_CALLBACK)
