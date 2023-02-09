from __future__ import annotations

from qtpy import QtWidgets as QtW
from magicgui.backends._qtpy.widgets import QBaseWidget
from magicgui.widgets import Widget
from tabulous.widgets import TableViewerWidget
from tabulous.types import TabPosition


class MagicTableViewer(Widget, TableViewerWidget):
    """
    A magicgui widget of table viewer.

    This class is a subclass of ``magicgui.widget.Widget`` so that it can be used
    in a compatible way with magicgui and napari.

    Parameters
    ----------
    tab_position: TabPosition or str
        Type of list-like widget to use.
    """

    def __init__(
        self,
        *,
        tab_position: TabPosition | str = TabPosition.top,
        name: str = "",
        label: str = None,
        tooltip: str | None = None,
        visible: bool | None = None,
        enabled: bool = True,
        show: bool = False,
    ):
        super().__init__(
            widget_type=QBaseWidget,
            backend_kwargs={"qwidg": QtW.QWidget},
            name=name,
            label=label,
            tooltip=tooltip,
            visible=visible,
            enabled=enabled,
        )
        TableViewerWidget.__init__(self, tab_position=tab_position, show=False)
        mgui_native: QtW.QWidget = self._widget._mgui_get_native_widget()
        mgui_native.setLayout(QtW.QVBoxLayout())
        mgui_native.layout().addWidget(self._qwidget)
        mgui_native.setContentsMargins(0, 0, 0, 0)
        if show:
            self.show(run=False)

    @property
    def native(self):
        try:
            return TableViewerWidget.native.fget(self)
        except AttributeError:
            return Widget.native.fget(self)
