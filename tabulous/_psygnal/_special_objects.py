from __future__ import annotations

from typing import Any, TYPE_CHECKING
import weakref

if TYPE_CHECKING:
    from tabulous._qt._table import QMutableTable


class RowCountGetter:
    def __init__(self, qtable: QMutableTable):
        self._qtable = weakref.ref(qtable)

    def __int__(self) -> int:
        return len(self._qtable().getDataFrame())

    def __float__(self) -> float:
        return float(self.__int__())

    def __add__(self, other: Any):
        return self.__int__() + other

    def __sub__(self, other: Any):
        return self.__int__() - other

    def __mul__(self, other: Any):
        return self.__int__() * other

    def __truediv__(self, other: Any):
        return self.__int__() / other

    def __floordiv__(self, other: Any):
        return self.__int__() // other

    def __mod__(self, other: Any):
        return self.__int__() % other

    def __pow__(self, other: Any):
        return self.__int__() ** other

    def __radd__(self, other: Any):
        return other + self.__int__()

    def __rsub__(self, other: Any):
        return other - self.__int__()

    def __rmul__(self, other: Any):
        return other * self.__int__()

    def __rtruediv__(self, other: Any):
        return other / self.__int__()

    def __rfloordiv__(self, other: Any):
        return other // self.__int__()

    def __rmod__(self, other: Any):
        return other % self.__int__()

    def __rpow__(self, other: Any):
        return other ** self.__int__()

    def __repr__(self) -> str:
        return str(int(self))

    def __index__(self) -> int:
        return self.__int__()
