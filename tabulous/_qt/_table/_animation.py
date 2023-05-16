from __future__ import annotations

from typing import TYPE_CHECKING, Callable
from abc import ABC, abstractmethod
from contextlib import contextmanager

from qtpy import QtCore, QtWidgets as QtW

if TYPE_CHECKING:
    from ._base import QBaseTable


class _Animation(ABC):
    def __init__(self, parent: QBaseTable):
        self._parent = parent
        self._anim = QtCore.QVariantAnimation(parent)
        self._anim.setDuration(100)
        self._anim.valueChanged.connect(self._on_animate)
        self._index = 0
        self._count = 1
        self._use_anim = True

    @abstractmethod
    def _get_header(self) -> QtW.QHeaderView:
        """Get the header object."""

    def start(self, idx: int, count: int):
        if not self._use_anim:
            return None
        self._index = idx
        self._count = count
        self._init_spans = [
            self._get_header().sectionSize(i)
            for i in range(self._index, self._index + self._count)
        ]
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    @contextmanager
    def using_animation(self, use_anim: bool = True):
        """Context manager to enable/disable animation."""
        _old = self._use_anim
        self._use_anim = use_anim
        try:
            yield None
        finally:
            self._use_anim = _old

    def _on_animate(self, ratio: float):
        header = self._get_header()
        for i, span in enumerate(self._init_spans):
            header.resizeSection(self._index + i, int(span * ratio))

    def connect(self, fn: Callable[[], None]):
        """Connect to the finished event of the animation."""
        if not self._use_anim:
            return fn()

        @self._anim.finished.connect
        def _f():
            try:
                with self._parent._mgr.blocked():
                    fn()
            finally:
                self._anim.finished.disconnect(_f)

        return _f


class ColumnAnimation(_Animation):
    def _get_header(self):
        return self._parent._qtable_view.horizontalHeader()


class RowAnimation(_Animation):
    def _get_header(self):
        return self._parent._qtable_view.verticalHeader()
