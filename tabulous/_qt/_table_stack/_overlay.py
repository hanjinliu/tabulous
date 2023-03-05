from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt
from superqt.utils import WorkerBase, FunctionWorker, GeneratorWorker
from .._progress import QCircularProgressBar
from .._titlebar import QTitleBar

if TYPE_CHECKING:
    from ._tabwidget import QTabbedTableStack


class Anchor(Enum):
    """Anchor position"""

    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class _QOverlayBase(QtW.QDialog):
    def __init__(self, parent: QTabbedTableStack):
        """The overlay widget appears at the fixed position."""
        super().__init__(parent, Qt.WindowType.SubWindow)
        self._widget = None

        titlebar = QTitleBar("", self)
        titlebar.closeSignal.connect(self.hide)
        self._title_bar = titlebar
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.setSpacing(0)
        _layout.addWidget(titlebar)

        self.setLayout(_layout)

        parent.resizedSignal.connect(self.alignToParent)
        self.setAnchor(Anchor.bottom_right)
        self.setVisible(False)

    def addWidget(self, widget: QtW.QWidget):
        """Set the central widget."""
        if self._widget is not None:
            self.removeWidget()
        self.layout().addWidget(widget)
        self.resize(widget.sizeHint() + self._title_bar.sizeHint())
        self._widget = widget
        self.alignToParent()

    def removeWidget(self):
        """Remove the central widget."""
        self._widget.setParent(None)
        self._widget = None
        self.resize(QtCore.QSize(0, 0))

    def widget(self) -> QtW.QWidget:
        """The central widget."""
        return self._widget

    def anchor(self) -> Anchor:
        """Anchor position."""
        return self._anchor

    def setAnchor(self, anc: Anchor | str) -> None:
        """Set anchor position of the overlay widget."""
        self._anchor = Anchor(anc)
        return self.alignToParent()

    def title(self) -> str:
        """Title of the overlay widget."""
        return self._title_bar.title()

    def setTitle(self, title: str) -> None:
        """Set the title of the overlay widget."""
        return self._title_bar.setTitle(title)

    def show(self):
        """Show the overlay widget with animation."""
        super().show()
        self.alignToParent()
        return None

    def hide(self) -> None:
        """Hide the overlay widget with animation."""
        self.parentWidget().parent().setCellFocus()
        return super().hide()

    def alignToParent(self):
        """Position widget at the bottom right edge of the parent."""
        if not self.isVisible():
            return
        qtable = self.parentWidget()
        # if not qtable or qtable.isEmpty():
        if not qtable:
            return
        if self._anchor == Anchor.bottom_left:
            self.alignBottomLeft()
        elif self._anchor == Anchor.bottom_right:
            self.alignBottomRight()
        elif self._anchor == Anchor.top_left:
            self.alignTopLeft()
        elif self._anchor == Anchor.top_right:
            self.alignTopRight()
        else:
            raise RuntimeError

    def viewRect(self) -> QtCore.QRect:
        """Return the parent table rect."""
        parent = self.parentWidget()
        if parent.isEmpty():
            rect = parent.rect()
        else:
            qtable = parent.tableAtIndex(parent.currentIndex())
            wdt = qtable.widget(0)
            if wdt is None:
                rect = qtable.rect()
            else:
                rect = qtable.widget(0).rect()
        return rect

    def alignTopLeft(self, offset=(8, 8)):
        pos = self.viewRect().topLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignTopRight(self, offset=(26, 8)):
        pos = self.viewRect().topRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignBottomLeft(self, offset=(8, 8)):
        pos = self.viewRect().bottomLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    def alignBottomRight(self, offset=(26, 8)):
        pos = self.viewRect().bottomRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> QTabbedTableStack: ...
    # fmt: on


class QOverlayWidget(_QOverlayBase):
    """The overlay widget appears at the fixed position."""

    def __init__(self, parent: QTabbedTableStack, duration: int = 50):
        """
        The overlay widget appears at the fixed position.

        Parameters
        ----------
        parent : QTabbedTableStack
            Parent table stack
        duration : int, default is 50
            Animation duration in msec.
        """
        super().__init__(parent)

        effect = QtW.QGraphicsOpacityEffect(self)
        effect.setOpacity(0.9)
        self.setGraphicsEffect(effect)
        self._effect = effect
        self.opacity_anim = QtCore.QPropertyAnimation(self._effect, b"opacity", self)
        self._duration = duration
        self._timer: QtCore.QTimer | None = None

    def hideLater(self, sec: float = 5):
        """Hide overlay widget after a delay."""
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(int(sec * 1000))
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide)
        self._timer.start()
        return None

    def _hide(self):
        if self.isVisible():
            self.setVisible(False)
            self._timer = None
        return None

    def show(self):
        """Show the overlay widget with animation."""
        super().show()
        self.opacity_anim.setDuration(self._duration)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(0.9)
        self.opacity_anim.start()
        return None

    def hide(self) -> None:
        """Hide the overlay widget with animation."""
        self.parentWidget().parent().setCellFocus()
        self.opacity_anim.setDuration(self._duration)
        self.opacity_anim.setStartValue(0.9)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.start()

        @self.opacity_anim.finished.connect
        def _on_vanished():
            if self.isVisible():
                self.setVisible(False)
            self.opacity_anim.finished.disconnect()

        return None

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        if self._timer is not None:
            self._timer.stop()
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        if self._timer is not None:
            self._timer.start()
        return super().leaveEvent(a0)


class QInfoStack(_QOverlayBase):
    def __init__(self, parent: QTabbedTableStack):
        super().__init__(parent)
        self._list_widget = QtW.QListWidget()
        self.addWidget(self._list_widget)
        self.setAnchor(Anchor.bottom_left)

    def addWorker(self, worker: WorkerBase, desc: str, total: int = 0):
        pbar = QCircularProgressBar()
        pbar.setButtonState("square")
        if isinstance(worker, FunctionWorker):
            pbar.setValue(-1)

        elif isinstance(worker, GeneratorWorker):
            _nyield = 0

            @worker.yielded.connect
            def _increment(*_):
                nonlocal _nyield
                _nyield += 1
                if _nyield > total:
                    value = -1
                else:
                    value = _nyield / total * 100
                return pbar.setValue(value)

        else:
            raise TypeError(f"Unsupported worker type: {type(worker)}")

        @pbar.abortRequested.connect
        def _aborting():
            if not worker.abort_requested:
                pbar.setInfinite(True)
                worker.quit()

        item = QtW.QListWidgetItem()
        labeled_pbar = labeled_progressbar(desc, pbar)
        worker.started.connect(lambda: self._on_worker_started(item, labeled_pbar))
        worker.finished.connect(lambda: self._on_worker_finish(item))

    def _on_worker_started(self, item: QtW.QListWidgetItem, widget: QtW.QWidget):
        lw = self._list_widget
        lw.addItem(item)
        lw.setIndexWidget(lw.model().index(lw.count() - 1, 0), widget)
        self.adjustHeight()
        self.show()

    def _on_worker_finish(self, item: QtW.QListWidgetItem):
        lw = self._list_widget
        lw.takeItem(lw.row(item))
        if lw.count() == 0:
            self.hide()
        else:
            self.adjustHeight()

    def adjustHeight(self):
        height = 20 * min(3, self._list_widget.count()) + 6
        self._list_widget.setFixedHeight(height)
        self.setFixedHeight(height + self._title_bar.sizeHint().height())
        self.alignToParent()


def labeled_progressbar(label: str, pbar: QCircularProgressBar):
    w = QtW.QWidget()
    _layout = QtW.QHBoxLayout(w)
    _layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(_layout)
    label_widget = QtW.QLabel(label)
    _layout.addWidget(label_widget, alignment=Qt.AlignmentFlag.AlignLeft)
    pbar.setRadius(8)
    pbar.setBarWidth(3)
    pbar.setFixedSize(20, 20)
    _layout.addWidget(pbar, alignment=Qt.AlignmentFlag.AlignRight)
    return w
