from __future__ import annotations

from typing import Callable
from pathlib import Path
from qtpy import QtGui, QtCore, QtSvg
from qtpy.QtCore import Qt
from functools import lru_cache

# These classes are mostly copied from napari/_qt/qt_resources/_svg.py
# See https://github.com/napari/napari/blob/main/napari/_qt/qt_resources/_svg.py


class SVGBufferIconEngine(QtGui.QIconEngine):
    def __init__(self, xml: str | bytes) -> None:
        if isinstance(xml, str):
            xml = xml.encode("utf-8")
        self.data = QtCore.QByteArray(xml)
        super().__init__()

    def paint(self, painter: QtGui.QPainter, rect, mode, state):
        """Paint the icon int ``rect`` using ``painter``."""
        renderer = QtSvg.QSvgRenderer(self.data)
        renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        renderer.render(painter, QtCore.QRectF(rect))

    def clone(self):
        """Required to subclass abstract QIconEngine."""
        return SVGBufferIconEngine(self.data)

    def pixmap(self, size, mode, state):
        """Return the icon as a pixmap with requested size, mode, and state."""
        img = QtGui.QImage(size, QtGui.QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        pixmap = QtGui.QPixmap.fromImage(img, Qt.ImageConversionFlag.NoFormatConversion)
        painter = QtGui.QPainter(pixmap)
        self.paint(painter, QtCore.QRect(QtCore.QPoint(0, 0), size), mode, state)
        return pixmap


class QColoredSVGIcon(QtGui.QIcon):
    _COLOR_ARG = "#000000"

    def __init__(
        self,
        xml: str,
        color: str = "#000000",
        converter: Callable[[QtGui.QColor], QtGui.QColor] = lambda x: x,
    ) -> None:
        self._color = QtGui.QColor(color)
        col = converter(self._color)
        self._xml = xml
        colorized = xml.replace(self._COLOR_ARG, col.name())
        super().__init__(SVGBufferIconEngine(colorized))

    @lru_cache
    def colored(
        self,
        color: str = "#000000",
    ) -> QColoredSVGIcon:
        return QColoredSVGIcon(self._xml, color)

    @classmethod
    def fromfile(cls: type[QColoredSVGIcon], path: str | Path, color="#000000"):
        with open(path) as f:
            xml = f.read()
        return cls(xml, color=color)

    def color(self) -> QtGui.QColor:
        """Color of the icon"""
        return self._color

    def with_converted(
        self, converter: Callable[[QtGui.QColor], QtGui.QColor]
    ) -> QColoredSVGIcon:
        return QColoredSVGIcon(self._xml, color=self._color.name(), converter=converter)
