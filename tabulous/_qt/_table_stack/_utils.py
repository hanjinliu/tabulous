from __future__ import annotations
from qtpy import QtWidgets as QtW, QtCore


def create_temporal_line_edit(
    rect: QtCore.QRect,
    parent: QtW.QWidget, 
    text: str,
) -> QtW.QLineEdit:
    line = QtW.QLineEdit(parent=parent)
    edit_geometry = line.geometry()
    edit_geometry.setWidth(rect.width())
    edit_geometry.setHeight(rect.height())
    edit_geometry.moveTo(rect.topLeft())
    line.setGeometry(edit_geometry)
    line.setText(text)
    line.setHidden(False)
    line.setFocus()
    line.selectAll()
    return line