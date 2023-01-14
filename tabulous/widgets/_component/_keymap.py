from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Any
from ._base import Component

if TYPE_CHECKING:
    from tabulous.widgets._keymap_abc import SupportKeyMap


class KeyMap(Component["SupportKeyMap"]):
    def register(
        self,
        key: str,
        func: Callable[[SupportKeyMap], Any] | None = None,
        overwrite: bool = False,
    ):
        def wrapper(f):
            def _inner(*_):
                return f(self.parent)

            return self.parent._qwidget._keymap.bind(key, _inner, overwrite=overwrite)

        return wrapper if func is None else wrapper(func)

    def unregister(self, key: str) -> None:
        self.parent._qwidget._keymap.unbind(key)

    def press_key(self, key: str) -> None:
        self.parent._qwidget._keymap.press_key(key)
        return None


def bind(self: KeyMap, *args, **kwargs):
    import warnings

    warnings.warn(
        "Keycombo registration using `keymap.bind` is deprecated. Use "
        "`keymap.register` instead.",
        DeprecationWarning,
    )
    return self.parent._qwidget._keymap.bind(*args, **kwargs)


KeyMap.bind = bind  # backward compatibility
