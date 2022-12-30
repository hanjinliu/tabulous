from __future__ import annotations
from pathlib import Path
from qtpy import QtWidgets as QtW

from tabulous._qt._svg import QColoredSVGIcon


ICON_DIR = Path(__file__).parent.parent / "_icons"


class QColoredToolButton(QtW.QToolButton):
    """Tool button with colored icon."""

    def icon(self) -> QColoredSVGIcon:
        """Get colored svg icon."""
        return self._icon

    def setIcon(self, icon: QColoredSVGIcon | str | Path) -> None:
        """Set colored svg icon."""
        if isinstance(icon, (str, Path)):
            icon = QColoredSVGIcon.fromfile(icon)
        self._icon = icon
        return super().setIcon(icon)

    def updateColor(self, color):
        """Update svg color."""
        return self.setIcon(self.icon().colored(color))


class QMoreToolButton(QColoredToolButton):
    """Tool button that shows the menu when clicked."""

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("QToolButton::menu-indicator { image: none; }")
        self.setIcon(ICON_DIR / "more.svg")
        self.setPopupMode(QtW.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolTip("More ...")
