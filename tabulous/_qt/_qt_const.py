import sys
from pathlib import Path
from qtpy import QtGui, QT6

# Monospace font
if sys.platform == "win32":
    MonospaceFontFamily = "Consolas"
elif sys.platform == "darwin":
    MonospaceFontFamily = "Menlo"
else:
    MonospaceFontFamily = "Monospace"

ICON_DIR = Path(__file__).parent / "_icons"

if QT6:

    def foreground_color_role(qpalette: QtGui.QPalette) -> QtGui.QColor:
        return qpalette.color(
            QtGui.QPalette.ColorGroup.Normal, QtGui.QPalette.ColorRole.Text
        )

    def background_color_role(qpalette: QtGui.QPalette) -> QtGui.QColor:
        return qpalette.color(
            QtGui.QPalette.ColorGroup.Normal, QtGui.QPalette.ColorRole.Base
        )

else:

    def foreground_color_role(qpalette: QtGui.QPalette) -> QtGui.QColor:
        return qpalette.color(QtGui.QPalette.ColorRole.Foreground)

    def background_color_role(qpalette: QtGui.QPalette) -> QtGui.QColor:
        return qpalette.color(QtGui.QPalette.ColorRole.Background)
