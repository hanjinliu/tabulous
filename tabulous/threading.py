from __future__ import annotations

from typing import Callable
from superqt.utils import thread_worker as _thread_worker
from tabulous._qt._mainwindow import QMainWindow


def thread_worker(
    function: Callable | None = None,
    *,
    label: str | None = None,
    total: int = 0,
):
    def _inner(fn: Callable):
        return create_worker(fn, label=label, total=total)

    return _inner if function is None else _inner(function)


def create_worker(
    fn: Callable,
    *,
    label: str | None = None,
    total: int = 0,
):
    if label is None:
        label = fn.__name__
    worker_creator = _thread_worker(fn)

    def _create_worker(*args, **kwargs):
        viewer = QMainWindow.currentViewer()
        worker = worker_creator(*args, **kwargs)
        viewer.native._tablestack._info_stack.addWorker(
            worker, label=label, total=total
        )
        return worker

    return _create_worker
