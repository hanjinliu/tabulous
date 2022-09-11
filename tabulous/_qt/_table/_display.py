from __future__ import annotations
from typing import TYPE_CHECKING, Callable
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, QTimer, Signal
from ._base import QBaseTable, _QTableViewEnhanced, DataFrameModel

if TYPE_CHECKING:
    import pandas as pd


def _get_standard_icon(x):
    return QtW.QApplication.style().standardIcon(x)


class _QPlayButton(QtW.QToolButton):
    """The play/pause button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._RUN = _get_standard_icon(QtW.QStyle.StandardPixmap.SP_MediaPlay)
        self._PAUSE = _get_standard_icon(QtW.QStyle.StandardPixmap.SP_MediaPause)
        self.clicked.connect(self.switchRunning)
        self.setRunning(True)

    def running(self) -> bool:
        return self._running

    def setRunning(self, val: bool):
        self._running = val
        if val:
            self.setIcon(self._PAUSE)
        else:
            self.setIcon(self._RUN)
        return None

    def switchRunning(self, *_):
        return self.setRunning(not self.running())

    def copy(self, link: bool = True) -> _QPlayButton:
        new = self.__class__(self.parent())
        new.setRunning(self.running())
        if link:
            new.clicked.connect(self.click)
        return new


class _QTimerSpinBox(QtW.QSpinBox):
    timeout = Signal()

    def __init__(self, parent=None, value: int = 100):
        super().__init__(parent)
        self.setMinimum(10)
        self.setMaximum(10000)
        self.setSuffix(" ms")

        self._qtimer = QTimer()
        self._qtimer.setSingleShot(True)
        self._qtimer.setInterval(value)
        self._qtimer.setTimerType(Qt.TimerType.PreciseTimer)
        self.valueChanged.connect(self._qtimer.setInterval)
        self.valueChanged.connect(self._set_step)
        self._qtimer.timeout.connect(self.timeout.emit)
        self.setValue(value)

    def copy(self, link: bool = True) -> _QTimerSpinBox:
        new = self.__class__(value=self.value())
        if link:
            self.valueChanged.connect(new.setValue)
            new.valueChanged.connect(self.setValue)
        return new

    def start(self):
        return self._qtimer.start()

    def stop(self):
        return self._qtimer.stop()

    def toggleTimer(self):
        if self._qtimer.isActive():
            self._qtimer.stop()
        else:
            self._qtimer.start()
        return None

    def _set_step(self, val: int):
        nd = len(str(val))
        if nd == 2:
            step = 10
        else:
            step = 5 * 10 ** (nd - 2)
        self.setSingleStep(step)
        return None


class _QTableDisplayWidget(QtW.QWidget):
    _table_display: QTableDisplay | None = None
    _timer: _QTimerSpinBox | None = None
    _play_btn: _QPlayButton | None = None
    _qtable_view: _QTableViewEnhanced | None = None

    @classmethod
    def from_table_display(cls, table_display: QTableDisplay) -> _QTableDisplayWidget:
        """Create a new QTableDisplayWidget from an existing QTableDisplay."""
        self = cls.from_widgets(
            spinbox=table_display._timer,
            play_button=table_display._play_btn,
            qtable_view=table_display._qtable_view_,
        )

        table_display.loaded.connect(self._on_loaded)
        self._table_display = table_display

        return self

    def copy(self, link: bool = True) -> _QTableDisplayWidget:
        new = self.from_widgets(
            spinbox=self._table_display._timer.copy(link=link),
            play_button=self._table_display._play_btn.copy(link=link),
            qtable_view=self._table_display._qtable_view_.copy(link=link),
        )
        new._table_display = self._table_display
        if link:
            self._table_display.loaded.connect(new._on_loaded)
        return new

    @classmethod
    def from_widgets(
        cls,
        spinbox: _QTimerSpinBox,
        play_button: _QPlayButton,
        qtable_view: _QTableViewEnhanced,
    ) -> _QTableDisplayWidget:
        """Create a new QTableDisplay from existing widgets."""
        self = cls()
        self._timer = spinbox
        self._play_btn = play_button
        self._qtable_view = qtable_view

        _header = QtW.QWidget()
        _header_layout = QtW.QHBoxLayout()
        _header_layout.setContentsMargins(2, 2, 2, 2)
        _header_layout.addWidget(QtW.QLabel("Interval:"))

        _header_layout.addWidget(spinbox)
        _header_layout.addWidget(play_button)
        _header.setLayout(_header_layout)

        _main_layout = QtW.QVBoxLayout()
        _main_layout.setContentsMargins(0, 0, 0, 0)
        _main_layout.addWidget(_header)
        _main_layout.addWidget(qtable_view)
        self.setLayout(_main_layout)

        return self

    def _on_loaded(self):
        if self._play_btn.running():
            self._timer.start()
        else:
            self._timer.stop()
        return self._qtable_view._update_all()

    @property
    def _selection_model(self):
        return self._qtable_view._selection_model

    def _on_moving(self, src, dst):
        return self._qtable_view._on_moving(src, dst)

    def _on_moved(self, src, dst):
        return self._qtable_view._on_moved(src, dst)


# TODO: don't initialize filter and only accept function filter.
class QTableDisplay(QBaseTable):
    loaded = Signal()

    def __init__(
        self,
        parent: QtW.QWidget | None = None,
        loader: Callable[[], pd.DataFrame] = None,
        interval_ms: int = 1000,
    ):
        import pandas as pd

        self._timer = _QTimerSpinBox(value=interval_ms)
        self._play_btn = _QPlayButton()
        self._play_btn.clicked.connect(self._timer.toggleTimer)

        super().__init__(parent, pd.DataFrame([]))
        if loader is None:
            self._loader = lambda: pd.DataFrame([])
        else:
            self._loader = lambda: pd.DataFrame(loader())
        self._loading = False
        self._timer.timeout.connect(self._on_timeout)

        if self._play_btn.running():
            self._timer.start()

    if TYPE_CHECKING:

        def model(self) -> DataFrameModel:
            ...

    def _on_timeout(self):
        """Run refresh if needed."""
        if self._play_btn.running() and not self._loading:
            self._load_data()

    def loader(self) -> Callable:
        """Return the loader function."""
        return self._loader

    def setLoader(self, loader: Callable) -> None:
        """Set the loader function and refresh."""
        if not callable(loader):
            raise TypeError("loader must be callable")
        self._loader = loader
        return self._load_data()

    def getDataFrame(self) -> pd.DataFrame:
        return self._data_raw

    def setDataFrame(self, data: pd.DataFrame) -> None:
        self._data_raw = data
        self.model().df = data
        self._qtable_view.viewport().update()
        self._filtered_index = data.index
        self._filtered_columns = data.columns
        return

    def createModel(self):
        model = DataFrameModel(self)
        self._qtable_view.setModel(model)
        return None

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_

    @property
    def _central_widget(self) -> _QTableDisplayWidget:
        return self._central_widget_

    def createQTableView(self):
        self._qtable_view_ = _QTableViewEnhanced(self)

        wdt = _QTableDisplayWidget.from_table_display(self)
        self.addWidget(wdt)
        self._central_widget_ = wdt

    def _load_data(self) -> None:
        self._loading = True
        if self.isVisible():
            try:
                self._data_raw = self._loader()
            except Exception as e:
                return
            self.model().df = self._data_raw
            self._filtered_index = self._data_raw.index
            self._filtered_columns = self._data_raw.columns

        self._loading = False
        self.loaded.emit()
        return None

    def running(self) -> bool:
        """True if the loader is running."""
        return self._play_btn.running()

    def setRunning(self, running: bool) -> None:
        """Set the loader running state."""
        self._play_btn.setRunning(running)
        return None

    def interval(self) -> int:
        return self._timer._qtimer.interval()

    def setInterval(self, interval: int) -> None:
        return self._timer._qtimer.setInterval(interval)
