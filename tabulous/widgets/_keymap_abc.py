from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING
from ._component import KeyMap

if TYPE_CHECKING:
    from tabulous._qt._mainwindow import _QtMainWidgetBase
    from tabulous._qt._table import QBaseTable


class SupportKeyMap(ABC):
    _qwidget: QBaseTable | _QtMainWidgetBase

    keymap = KeyMap()
