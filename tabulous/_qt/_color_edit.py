from __future__ import annotations
from typing import Iterable
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal

from magicgui.widgets._bases import ValueWidget
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from magicgui.application import use_app

from ..color import normalize_color, rgba_to_str


# modified from napari/_qt/widgets/qt_color_swatch.py
class QColorSwatch(QtW.QFrame):
    colorChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._qcolor: QtGui.QColor = QtGui.QColor(255, 255, 255, 255)
        self.colorChanged.connect(self._update_swatch_style)
        self.setMinimumWidth(40)

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        """Get RBGA tuple from QColor."""
        return self._qcolor.getRgb()

    def heightForWidth(self, w: int) -> int:
        return int(w * 0.667)

    def _update_swatch_style(self, _=None) -> None:
        rgba = f'rgba({",".join(str(x) for x in self.rgba)})'
        return self.setStyleSheet("QColorSwatch {background-color: " + rgba + ";}")

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Show QColorPopup picker when the user clicks on the swatch."""
        if event.button() == Qt.MouseButton.LeftButton:
            dlg = QtW.QColorDialog(self._qcolor, self)
            dlg.setOptions(QtW.QColorDialog.ColorDialogOption.ShowAlphaChannel)
            ok = dlg.exec_()
            if ok:
                self.setQColor(dlg.selectedColor())

    def qColor(self) -> QtGui.QColor:
        return self._qcolor

    def setQColor(self, color: QtGui.QColor) -> None:
        old_color = self._qcolor
        self._qcolor = color
        if self._qcolor.getRgb() != old_color.getRgb():
            self.colorChanged.emit()


class QColorLineEdit(QtW.QLineEdit):
    colorChanged = Signal()

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._qcolor = QtGui.QColor(255, 255, 255, 255)
        self.editingFinished.connect(self._emit_color_changed)

    def qColor(self) -> QtGui.QColor:
        """Get color as QtGui.QColor object"""
        return self._qcolor

    def setQColor(self, color: QtGui.QColor):
        self._qcolor = color
        text = rgba_to_str(color.getRgb())
        self.setText(text)

    def _emit_color_changed(self):
        text = self.text()
        try:
            rgba = normalize_color(text)
        except ValueError:
            self.setQColor(self._qcolor)
        else:
            if self._qcolor.getRgb() != rgba:
                self._qcolor = QtGui.QColor(*rgba)
                self.colorChanged.emit()


class QColorEdit(QtW.QWidget):
    colorChanged = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QHBoxLayout()
        self._color_swatch = QColorSwatch(self)
        self._line_edit = QColorLineEdit(self)
        _layout.addWidget(self._color_swatch)
        _layout.addWidget(self._line_edit)
        self.setLayout(_layout)

        self._color_swatch.colorChanged.connect(self._on_swatch_changed)
        self._line_edit.colorChanged.connect(self._on_line_edit_edited)

    def qColor(self):
        """Return the current color."""
        return self._color_swatch._qcolor

    def color(self) -> tuple[int, int, int, int]:
        return self._color_swatch.rgba

    def setColor(self, color: QtGui.QColor | str | Iterable[int]):
        """Set value as the current color."""
        if not isinstance(color, QtGui.QColor):
            color = QtGui.QColor(*normalize_color(color))
        self._line_edit.setQColor(color)
        self._color_swatch.setQColor(color)

    def _on_line_edit_edited(self):
        self._line_edit.blockSignals(True)
        qcolor = self._line_edit.qColor()
        self._color_swatch.setQColor(qcolor)
        self._line_edit.blockSignals(False)
        self.colorChanged.emit(qcolor.getRgb())

    def _on_swatch_changed(self):
        self._color_swatch.blockSignals(True)
        qcolor = self._color_swatch.qColor()
        self._line_edit.setQColor(qcolor)
        self._color_swatch.blockSignals(False)
        self.colorChanged.emit(qcolor.getRgb())


class _ColorEdit(QBaseValueWidget):
    _qwidget: QColorEdit

    def __init__(self):
        super().__init__(QColorEdit, "color", "setColor", "colorChanged")


class ColorEdit(ValueWidget):
    """
    A widget for editing colors.

    Parameters
    ----------
    value : tuple of int or str
        RGBA color, color code or standard color name.
    """

    def __init__(self, **kwargs):
        app = use_app()
        assert app.native
        kwargs["widget_type"] = _ColorEdit
        super().__init__(**kwargs)
