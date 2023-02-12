from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui

from tabulous.color import normalize_color
from tabulous._qt._svg import QColoredSVGIcon


ICON_DIR = Path(__file__).parent.parent / "_icons"


class QColoredToolButton(QtW.QToolButton):
    """Tool button with colored icon."""

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("QToolButton::menu-indicator { image: none; }")

    def icon(self) -> QColoredSVGIcon:
        """Get colored svg icon."""
        return self._icon

    def setIcon(self, icon: QColoredSVGIcon | str | Path) -> None:
        """Set colored svg icon."""
        if isinstance(icon, (str, Path)):
            icon = QColoredSVGIcon.fromfile(icon)
        self._icon = icon
        return super().setIcon(icon)

    def updateColor(self, color: str):
        """Update svg color."""
        icon = self.icon().colored(color)
        if not self.isEnabled():
            icon = icon.with_converted(self._mix_with_background)
        self.setIcon(icon)
        return None

    def setEnabled(self, a0: bool) -> None:
        if self.isEnabled() != a0:
            # blend icon color with background color
            if a0:
                self.setIcon(self.icon().with_converted(lambda x: x))
            else:
                self.setIcon(self.icon().with_converted(self._mix_with_background))
        return super().setEnabled(a0)

    def backgroundColor(self) -> QtGui.QColor:
        """Get background color."""
        return self.palette().color(self.backgroundRole())

    def _mix_with_background(self, color: QtGui.QColor) -> QtGui.QColor:
        """Mix color with background color."""
        bg = self.palette().color(self.backgroundRole()).getRgb()
        return QtGui.QColor(*normalize_color(color.getRgb()).mix(bg, 0.7))


class QMoreToolButton(QColoredToolButton):
    """Tool button that shows the menu when clicked."""

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setIcon(ICON_DIR / "more.svg")
        self.setPopupMode(QtW.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolTip("More ...")
