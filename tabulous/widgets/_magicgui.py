from __future__ import annotations
from typing import Any

from qtpy import QtWidgets as QtW
from magicgui.widgets import Widget
from magicgui.backends._qtpy.widgets import QBaseWidget

from tabulous.widgets._table import Table, SpreadSheet


class MagicTable(Widget, Table):
    def __init__(
        self,
        data: Any | None = None,
        *,
        name: str = "",
        editable: bool = False,
        label: str = None,
        tooltip: str | None = None,
        visible: bool | None = None,
        enabled: bool = True,
        gui_only: bool = False,
    ):
        Table.__init__(self, data, name=name, editable=editable)
        super().__init__(
            widget_type=QBaseWidget,
            backend_kwargs={"qwidg": QtW.QWidget},
            name=name,
            label=label,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
            gui_only=gui_only,
        )
        mgui_native: QtW.QWidget = self._widget._mgui_get_native_widget()
        mgui_native.setLayout(QtW.QVBoxLayout())
        mgui_native.layout().addWidget(self._qwidget)
        mgui_native.setContentsMargins(0, 0, 0, 0)

    @property
    def native(self):
        return Table.native.fget(self)


class MagicSpreadSheet(Widget, SpreadSheet):
    def __init__(
        self,
        data: Any | None = None,
        *,
        name: str = "",
        editable: bool = True,
        label: str = None,
        tooltip: str | None = None,
        visible: bool | None = None,
        enabled: bool = True,
        gui_only: bool = False,
    ):
        SpreadSheet.__init__(self, data, name=name, editable=editable)
        super().__init__(
            widget_type=QBaseWidget,
            backend_kwargs={"qwidg": QtW.QWidget},
            name=name,
            label=label,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
            gui_only=gui_only,
        )
        mgui_native: QtW.QWidget = self._widget._mgui_get_native_widget()
        mgui_native.setLayout(QtW.QVBoxLayout())
        mgui_native.layout().addWidget(self._qwidget)
        mgui_native.setContentsMargins(0, 0, 0, 0)

    @property
    def native(self):
        return SpreadSheet.native.fget(self)
