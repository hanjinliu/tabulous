from types import ModuleType
from typing import Callable, Generic, TypeVar
import concurrent.futures


_T = TypeVar("_T")


class AsyncImporter(Generic[_T]):
    """
    Asynchronously import something.

    Usage
    -----
    >>> def import_plt():
    ...     from matplotlib import pyplot as plt
    ...     return plt
    >>> import_plt = AsyncImporter(import_plt)
    >>> plt = import_plt.get()
    """

    def __init__(self, import_func: Callable[[], _T]) -> None:
        self._target = import_func
        self._future: "concurrent.futures.Future[_T] | None" = None

    def run(self) -> None:
        if self._future is None or self._future.done():
            self._future = concurrent.futures.ThreadPoolExecutor().submit(self._target)

    def get(self, timeout: float = None) -> _T:
        self.run()
        return self._future.result(timeout)

    __call__ = get


@AsyncImporter
def import_plt() -> ModuleType:
    from matplotlib import pyplot as plt

    return plt


@AsyncImporter
def import_scipy() -> ModuleType:
    import scipy

    return scipy
