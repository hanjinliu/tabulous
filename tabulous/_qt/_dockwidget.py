from __future__ import annotations
from functools import reduce
from operator import ior
from qtpy.QtWidgets import QDockWidget as _QDockWidget, QMainWindow, QWidget
from qtpy.QtCore import Qt


class QtDockWidget(_QDockWidget):
    areas = {
        "left": Qt.LeftDockWidgetArea,
        "right": Qt.RightDockWidgetArea,
        "top": Qt.TopDockWidgetArea,
        "bottom": Qt.BottomDockWidgetArea,
    }

    def __init__(
        self,
        parent: QMainWindow,
        widget: QWidget,
        *,
        name: str = "",
        area: str = "right",
        allowed_areas: list[str] = None,
    ):
        super().__init__(name, parent)
        areas = self.__class__.areas

        if allowed_areas:
            if not isinstance(allowed_areas, (list, tuple)):
                raise TypeError("`allowed_areas` must be a list or tuple")

            if any(area not in areas for area in allowed_areas):
                raise ValueError(
                    f"all allowed_areas argument must be in {set(areas.keys())}"
                )
            allowed_areas = reduce(ior, [areas[a] for a in allowed_areas])
        else:
            allowed_areas = Qt.AllDockWidgetAreas
        self.qt_area = areas[area]
        self.setAllowedAreas(allowed_areas)
        self.setWidget(widget)
        self.setMinimumHeight(50)
        self.setMinimumWidth(50)
