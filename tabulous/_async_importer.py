import threading
from types import ModuleType
from typing import Callable, Generic, TypeVar

THREAD: "threading.Thread | None" = None

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
        self._thread: "threading.Thread | None" = None

    def run(self) -> None:
        with threading.Lock():
            if self._thread is None:
                self._thread = threading.Thread(target=self._target, daemon=True)
                self._thread.start()
            else:
                self._thread.join()

    def get(self, ignore_error: bool = True) -> _T:
        try:
            self.run()
        except Exception as e:
            if ignore_error:
                return None
            else:
                raise e
        else:
            return self._target()

    __call__ = get


@AsyncImporter
def import_plt() -> ModuleType:
    from matplotlib import pyplot as plt

    return plt


@AsyncImporter
def import_scipy() -> ModuleType:
    import scipy

    return scipy
