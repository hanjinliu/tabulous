from __future__ import annotations
from typing import Callable, TYPE_CHECKING
import numpy as np
import pandas as pd
from qtpy import QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from ._base import AbstractDataFrameModel, QBaseTable
from ._readers import TextFileReader, AbstractReader

if TYPE_CHECKING:
    from ._base._enhanced_table import _QTableViewEnhanced

_N_CHUNK = 1000
_VERY_BIG_NUMBER = 2147483647


def _no_loader(start: int, stop: int) -> tuple[pd.DataFrame, bool]:
    return pd.DataFrame([]), True


class LazyLoaderModel(AbstractDataFrameModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._row_count = 0
        self._col_count = 0

        # _loader returns a loaded chunk of data and a boolean indicating if it is
        # the last chunk
        self._loader: Callable[[int, int], tuple[pd.DataFrame, bool]] = _no_loader
        self._current_offset = 0

    def _set_reader(self, reader: AbstractReader):
        self._loader = reader.read_range
        head, _ = self._loader(0, 1)
        self._row_count = _VERY_BIG_NUMBER
        self._col_count = head.columns.size
        return None

    def _load_chunk(self, chunk_start: int, chunk_stop: int) -> None:
        self._current_offset = chunk_start
        self._df, ended = self._loader(chunk_start, chunk_stop)
        if ended:
            self._row_count = chunk_start + self._df.shape[0]
        return None

    def _model_index_to_tuple(self, index: QtCore.QModelIndex):
        r, c = super()._model_index_to_tuple(index)
        if r < self._current_offset:
            start = max(self._current_offset - _N_CHUNK // 2, 0)
            self._load_chunk(start, start + _N_CHUNK)
        elif r >= self._current_offset + _N_CHUNK:
            start = self._current_offset + _N_CHUNK // 2
            self._load_chunk(start, start + _N_CHUNK)
        return r - self._current_offset, c

    def rowCount(self, parent: QtCore.QModelIndex = None) -> int:
        return self._row_count

    def columnCount(self, parent: QtCore.QModelIndex = None) -> int:
        return self._col_count


class QTableLazyLoader(QBaseTable):
    def __init__(self, path, parent: QtW.QWidget | None = None):
        import pandas as pd

        super().__init__(parent, pd.DataFrame([]))
        self.setPath(path)

    def createModel(self) -> None:
        """Create spreadsheet model."""
        model = LazyLoaderModel(self)
        self._qtable_view.setModel(model)
        return None

    def createQTableView(self) -> None:
        from ._base._enhanced_table import _QTableViewEnhanced

        self._qtable_view_ = _QTableViewEnhanced(self)
        self.addWidget(self._qtable_view_)
        return None

    @property
    def _qtable_view(self) -> _QTableViewEnhanced:
        return self._qtable_view_

    # fmt: off
    if TYPE_CHECKING:
        def model(self) -> LazyLoaderModel: ...
    # fmt: on

    def setPath(self, path: str):
        self.model()._set_reader(TextFileReader(path))

    def getDataFrame(self) -> pd.DataFrame:
        return None

    def setDataFrame(self, data: pd.DataFrame) -> None:
        pass
