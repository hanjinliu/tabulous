from __future__ import annotations

from typing import (
    Any,
    Callable,
    TYPE_CHECKING,
)
from functools import wraps, partial

if TYPE_CHECKING:
    from typing_extensions import Self, ParamSpec
    from ._keymap import QtKeys

    _P = ParamSpec("_P")


class BoundCallback(partial):
    desc: str

    def __new__(
        cls,
        func: Callable[_P, Any],
        /,
        *,
        desc: str = "",
        keys: QtKeys | None = None,
        kwargs: dict[str, Any] = {},
    ) -> Self:
        kwargs = kwargs.copy()

        import inspect

        sig = inspect.signature(func)
        params = dict(sig.parameters)

        # check argument names if **kwargs is not in the function
        if not any(
            param.kind
            in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for param in params.values()
        ):
            new_params: dict[str, inspect.Parameter] = {}
            for name in kwargs:
                if name not in params:
                    raise TypeError(
                        f"{func} does not accept keyword argument {name!r}."
                    )

                new_params[name] = params[name].replace(default=kwargs[name])
            params.update(new_params)
            sig = sig.replace(parameters=list(params.values()))

        self: Self = partial.__new__(cls, func, **kwargs)
        self.desc = desc
        self.keys = keys
        wraps(func)(self)
        self.__signature__ = sig
        return self

    @property
    def desc(self) -> str:
        """Description of function."""
        return self._desc

    @desc.setter
    def desc(self, val) -> None:
        if val is not None:
            if not isinstance(val, str):
                raise TypeError("description must be string.")
            desc = val
        else:
            from docstring_parser import parse

            _doc = getattr(self.func, "__doc__", "")
            if _doc == "":
                return _doc
            doc = parse(_doc)
            desc = doc.short_description

        self._desc = desc
        return None

    @property
    def keys(self) -> QtKeys:
        """Key bound to the callback."""
        return self._keys

    @keys.setter
    def keys(self, val):
        # TODO: normalize
        self._keys = val

    def __repr__(self) -> str:
        cls_str = type(self).__name__
        fn_str = getattr(self.func, "__name__", repr(self.func))
        sig_str = str(self.__signature__)  # things like (x: int)
        return f"{cls_str}<{fn_str}{sig_str}>"

    def __get__(self, obj, objtype=None) -> BoundCallback:
        if obj is None:
            return self
        return BoundCallback(
            self.func.__get__(obj, objtype),
            desc=self.desc,
            keys=self.keys,
            kwargs=self.keywords,
        )
