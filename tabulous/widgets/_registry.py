from __future__ import annotations
from functools import partial
from typing import Any, TYPE_CHECKING, Callable, overload, TypeVar, Generic

if TYPE_CHECKING:
    from tabulous._qt._action_registry import QActionRegistry

_P = TypeVar("_P")
_T = TypeVar("_T")


class SupportActionRegistration(Generic[_P, _T]):
    def _get_qregistry(self) -> QActionRegistry:
        raise NotImplementedError()

    @property
    def parent(self) -> _P:
        raise NotImplementedError()

    def register_action(self, *args):
        """Register an contextmenu action."""
        import warnings

        warnings.warn(
            "`register_action` is deprecated. Use `register` instead.",
            DeprecationWarning,
        )

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
            raise TypeError(f"No overloaded method matched the input ({arg}).")

        def wrapper(f: Callable[[int], Any]):
            reg.registerAction(loc, f)
            return f

        return wrapper if func is None else wrapper(func)

    # fmt: off
    @overload
    def register(self, location: str) -> Callable[[Callable[[_P, _T], Any]], Callable[[_P, _T], Any]]: ...  # noqa: E501
    @overload
    def register(self, location: str, func: Callable[[_P, _T], Any]) -> Callable[[_P, _T], Any]: ...  # noqa: E501
    @overload
    def register(self, func: Callable[[_P, _T], Any]) -> Callable[[_P, _T], Any]: ...  # noqa: E501
    # fmt: on

    def register(self, *args):
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
                "1. register(location: str)\n"
                "2. register(func: Callable)\n"
                "3. register(location: str, func: Callable)"
            )

        def wrapper(f: Callable[[_P, int], Any]):
            meth = partial(f, self.parent)
            reg.registerAction(loc, meth)
            return f

        return wrapper if func is None else wrapper(func)
