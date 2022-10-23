from __future__ import annotations

from types import ModuleType


class Namespace:
    """Namespace used in cell edit"""

    def __init__(self):
        import numpy, pandas

        self._ns: dict[str, ModuleType] = {"np": numpy, "pd": pandas}

    def value(self) -> dict[str, ModuleType]:
        return self._ns.copy()

    def update(self, ns: dict[str, ModuleType]) -> None:
        return self._ns.update(ns)

    def remove(self, names: list[str]) -> None:
        for name in names:
            self._ns.pop(name, None)
        return None
