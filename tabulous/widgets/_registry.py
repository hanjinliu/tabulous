from __future__ import annotations

import re
from typing import Any, TYPE_CHECKING, Callable, overload, TypeVar, Generic
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from tabulous._qt._action_registry import QActionRegistry

_S = TypeVar("_S")
_T = TypeVar("_T")
_P = ParamSpec("_P")


class SupportActionRegistration(Generic[_S, _T]):
    """An abstract class to support action registration to right-click contextmenu."""

    def _get_qregistry(self) -> QActionRegistry:
        raise NotImplementedError()

    @property
    def parent(self) -> _S:
        raise NotImplementedError()

    # fmt: off
    @overload
    def register(self, location: str) -> Callable[[Callable[[_S, _T], Any]], Callable[[_S, _T], Any]]: ...  # noqa: E501
    @overload
    def register(self, location: str, func: Callable[[_S, _T], Any]) -> Callable[[_S, _T], Any]: ...  # noqa: E501
    @overload
    def register(self, func: Callable[[_S, _T], Any]) -> Callable[[_S, _T], Any]: ...  # noqa: E501
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

        def wrapper(f: Callable[[_S, int], Any]):
            meth = _NormalizedFunction(f, self.parent)
            reg.registerAction(loc, meth)
            return f

        return wrapper if func is None else wrapper(func)

    def unregister(self, location: str):
        """Unregister an contextmenu action."""
        self._get_qregistry().unregisterAction(location)


# e.g. f() takes from 0 to 1 positional arguments but 2 were given
_PATTERN = re.compile(r".*takes .* positional arguments? but (\d+) w.+ given")


class _NormalizedFunction(Generic[_P]):
    def __init__(self, f: Callable[_P, Any], parent) -> None:
        self._f = f
        self._parent = parent
        self._f_normed = f

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} of {self._f.__name__!r}>"

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs):
        try:
            out = self._f_normed(self._parent, *args, **kwargs)
        except TypeError as e:
            if _PATTERN.match(str(e)):
                import inspect

                sig = inspect.signature(self._f)
                nparams = len(sig.parameters)

                if nparams == 0:

                    def normed(parent, *args, **kwargs):
                        return self._f(**kwargs)

                else:

                    def normed(parent, *args, **kwargs):
                        return self._f(parent, *args[: nparams - 1], **kwargs)

                self._f_normed = normed
                out = normed(self._parent, *args)
            else:
                raise e
        return out

    @property
    def func(self):
        return self._f
