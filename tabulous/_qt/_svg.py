from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui, QtCore, QtSvg
from qtpy.QtCore import Qt
from functools import lru_cache

# These classes are mostly copied from napari/_qt/qt_resources/_svg.py
# See https://github.com/napari/napari/blob/main/napari/_qt/qt_resources/_svg.py

class SVGBufferIconEngine(QtGui.QIconEngine):
    def __init__(self, xml: str | bytes) -> None:
        if isinstance(xml, str):
            xml = xml.encode('utf-8')
        self.data = QtCore.QByteArray(xml)
        super().__init__()

    def paint(self, painter: QtGui.QPainter, rect, mode, state):
        """Paint the icon int ``rect`` using ``painter``."""
        renderer = QtSvg.QSvgRenderer(self.data)
        renderer.render(painter, QtCore.QRectF(rect))

    def clone(self):
        """Required to subclass abstract QIconEngine."""
        return SVGBufferIconEngine(self.data)

    def pixmap(self, size, mode, state):
        """Return the icon as a pixmap with requested size, mode, and state."""
        img = QtGui.QImage(size, QtGui.QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        pixmap = QtGui.QPixmap.fromImage(img, Qt.NoFormatConversion)
        painter = QtGui.QPainter(pixmap)
        self.paint(painter, QtCore.QRect(QtCore.QPoint(0, 0), size), mode, state)
        return pixmap


class QColoredSVGIcon(QtGui.QIcon):
    _COLOR_ARG = '#000000'
    
    def __init__(
        self,
        xml: str,
        color: str = "#000000",
    ) -> None:
        self._xml = xml
        colorized = xml.replace(self._COLOR_ARG, f'{color}')
        super().__init__(SVGBufferIconEngine(colorized))

    @lru_cache
    def colored(
        self,
        color: str = "#000000",
    ) -> 'QColoredSVGIcon':
        return QColoredSVGIcon(self._xml, color)
    
    @classmethod
    def fromfile(cls: type[QColoredSVGIcon], path: str | Path, color="#000000"):
        with open(path, "r") as f:
            xml = f.read()
        return cls(xml, color=color)
