from __future__ import annotations
from typing import Any, TYPE_CHECKING, Callable, overload, TypeVar

if TYPE_CHECKING:
    from tabulous._qt._action_registry import QActionRegistry

_F = TypeVar("_F")


class SupportActionRegistration:
    def _get_qregistry(self) -> QActionRegistry:
        raise NotImplementedError

    # fmt: off
    @overload
    def register_action(self, location: str) -> Callable[[_F], _F]: ...
    @overload
    def register_action(self, location: str, func: _F) -> _F: ...
    @overload
    def register_action(self, func: _F) -> _F: ...
    # fmt: on

    def register_action(self, *args):
        """Register an contextmenu action."""
        reg = self._get_qregistry()
        nargs = len(args)
        if nargs == 0 or nargs > 2:
            raise TypeError("One or two arguments are allowed.")
        if nargs == 1:
            arg = args[0]
            if callable(arg):
                loc, func = getattr(arg, "__name__", repr(arg)), arg
            else:
                loc, func = arg, None
        else:
            loc, func = args

        # check type
        if not isinstance(loc, str) or (func is not None and not callable(func)):
            arg = type(loc).__name__
            if func is not None:
                arg += f", {type(func).__name__}"
            raise TypeError(
                f"No overloaded method matched the input ({arg}).\n"
                "1. register_action(location: str)\n"
                "2. register_action(func: Callable)\n"
                "3. register_action(location: str, func: Callable)"
            )

        def wrapper(f: Callable[[int], Any]):
            reg.registerAction(loc, f)
            return f

        return wrapper if func is None else wrapper(func)
