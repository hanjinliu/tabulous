from __future__ import annotations
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Signal, Qt

if TYPE_CHECKING:
    from .._mainwindow import _QtMainWidgetBase


def find_parent_table_viewer(qwidget: _QtMainWidgetBase) -> _QtMainWidgetBase:
    x = qwidget
    while (parent := x.parent()) is not None:
        x = parent
        if hasattr(x, "_table_viewer"):
            return x
    raise RuntimeError
