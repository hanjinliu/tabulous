from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Any
import re
from ._base import Component

if TYPE_CHECKING:
    from tabulous.widgets._keymap_abc import SupportKeyMap

# e.g. f() takes 0 positional arguments but 1 was given
_PATTERN = re.compile(r".*takes 0 positional arguments but (\d+) w.+ given")


class KeyMap(Component["SupportKeyMap"]):
    def register(
        self,
        key: str,
        func: Callable[[SupportKeyMap], Any] | None = None,
        overwrite: bool = False,
    ):
        def wrapper(f):
            def _inner(*_):
                try:
                    out = f(self.parent)
                except TypeError as e:
                    if _PATTERN.match(str(e)):
                        out = f()
                    else:
                        raise e
                return out

            return self.parent._qwidget._keymap.bind(key, _inner, overwrite=overwrite)

        return wrapper if func is None else wrapper(func)

    def unregister(self, key: str) -> None:
        self.parent._qwidget._keymap.unbind(key)

    def press_key(self, key: str) -> None:
        self.parent._qwidget._keymap.press_key(key)
        return None
