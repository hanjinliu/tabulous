from __future__ import annotations

from types import FunctionType
from typing import MutableMapping, Any, TypeVar, Mapping

_T = TypeVar("_T", FunctionType, type)


class Namespace(MutableMapping[str, Any]):
    """Namespace used in cell edit"""

    def __init__(self):
        import numpy, pandas

        self._ns: dict[str, Any] = {"np": numpy, "pd": pandas}
        self._static = set(self._ns.keys())

    def __len__(self) -> int:
        return len(self._ns)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._ns!r})"

    def __iter__(self):
        return iter(self._ns)

    def _check_static(self, key: str):
        if key in self._static:
            raise ValueError(f"Cannot update {key!r}")

    def __getitem__(self, key: str) -> Any:
        return self._ns[key]

    def __setitem__(self, key: str, val: Any) -> None:
        self._check_static(key)
        self._ns[key] = val

    def __delitem__(self, key: str) -> None:
        self._check_static(key)
        del self._ns[key]

    def update(self, ns: Mapping[str, Any] = {}, /, **kwargs) -> None:
        ns = dict(**ns, **kwargs)
        if collision := set(ns.keys()) & self._static:
            raise ValueError(f"Cannot update {collision!r}")
        return self._ns.update(ns)

    def update_safely(self, ns: Mapping[str, Any] = {}, /, **kwargs) -> None:
        ns = dict(**ns, **kwargs)
        for k in self._static:
            ns.pop(k, None)
        return self._ns.update(ns)

    def add(self, obj: _T) -> _T:
        """A decorator to add an callable object to the namespace."""
        if callable(obj) or isinstance(obj, type):
            name = obj.__name__
            self[name] = obj
        else:
            raise TypeError(f"Expected to be used as a decorator, got {type(obj)}")
        return obj
