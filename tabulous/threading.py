from __future__ import annotations

from typing import Any, Callable, Generator, overload, TypeVar
from typing_extensions import ParamSpec
import inspect
from functools import lru_cache
from superqt.utils import (
    thread_worker as _thread_worker,
    GeneratorWorker,
    FunctionWorker,
)
from tabulous._qt._mainwindow import QMainWindow

__all__ = ["thread_worker"]

_Y = TypeVar("_Y")
_S = TypeVar("_S")
_R = TypeVar("_R")
_P = ParamSpec("_P")


@overload
def thread_worker(
    function: Callable[_P, Generator[_Y, _S, _R]],
    *,
    desc: str | None = None,
    total: int = 0,
) -> Callable[_P, GeneratorWorker[_Y, _S, _R]]:
    ...


@overload
def thread_worker(
    function: Callable[_P, _R],
    *,
    desc: str | None = None,
    total: int = 0,
) -> Callable[_P, FunctionWorker[_R]]:
    ...


@overload
def thread_worker(
    function: None = None,
    *,
    desc: str | None = None,
    total: int = 0,
) -> Callable[
    [Callable[_P, _R]], Callable[_P, FunctionWorker[_R] | GeneratorWorker[Any, Any, _R]]
]:
    ...


def thread_worker(function=None, *, desc=None, total=0):
    """
    Convert the returned value of a function into a worker.

    >>> from tabulous.threading import thread_worker
    >>> @thread_worker
    >>> def func():
    ...     time.sleep(1)

    Parameters
    ----------
    function : callable
        Function to be called in another thread.
    desc : str, optional
        Label that will shown beside the progress indicator. The function name
        will be used if not provided.
    total : int, default is 0
        Total number of steps for the progress indicator.
    """

    def _inner(fn: Callable):
        return create_worker(fn, desc=desc, total=total)

    return _inner if function is None else _inner(function)


def create_worker(
    fn: Callable,
    *,
    desc: str | None = None,
    total: int = 0,
):
    worker_constructor = _thread_worker(fn)
    sig = inspect.signature(fn)

    def _create_worker(*args, **kwargs):
        nonlocal desc, total
        bound = sig.bind_partial(*args, **kwargs)
        if desc is None:
            _desc = getattr(fn, "__name__", repr(fn))
        elif callable(desc):
            _desc = _call_with_filtered(desc, bound.arguments)
        else:
            _desc = desc
        if not isinstance(_desc, str):
            raise TypeError("`desc` did not return a str.")

        if callable(total):
            _total = _call_with_filtered(total, bound.arguments)
        else:
            _total = total
        if not isinstance(_total, int):
            raise TypeError("`total` did not return an int.")
        viewer = QMainWindow.currentViewer()
        worker = worker_constructor(*args, **kwargs)
        viewer.native._tablestack._info_stack.addWorker(
            worker, desc=_desc, total=_total
        )
        return worker

    return _create_worker


@lru_cache(maxsize=32)
def _make_filter(fn: Callable[..., _R]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    sig = inspect.signature(fn)
    arg_names: list[str] = []
    for name, param in sig.parameters.items():
        if param.kind in (
            param.POSITIONAL_ONLY,
            param.POSITIONAL_OR_KEYWORD,
            param.KEYWORD_ONLY,
        ):
            arg_names.append(name)
        elif param.kind == param.VAR_POSITIONAL:
            raise NotImplementedError("Cannot use *args or **kwargs")
        elif param.kind == param.VAR_KEYWORD:
            raise NotImplementedError("Cannot use *args or **kwargs")

    def _filter(kwargs: dict):
        return {k: v for k, v in kwargs.items() if k in arg_names}

    return _filter


def _call_with_filtered(fn: Callable[..., _R], kwargs: dict[str, Any]) -> _R:
    filt = _make_filter(fn)
    return fn(**filt(kwargs))
