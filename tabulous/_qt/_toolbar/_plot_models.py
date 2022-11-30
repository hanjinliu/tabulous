from __future__ import annotations
from typing import Iterator, TYPE_CHECKING, NamedTuple
import weakref
import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

# NOTE: Axes should be imported here!
from tabulous.widgets import TableBase
from tabulous._selection_op import SelectionOperator
from tabulous._magicgui import Axes

if TYPE_CHECKING:
    from matplotlib.collections import PathCollection
    from tabulous._qt._plot import QtMplPlotCanvas

logger = logging.getLogger(__name__)


class PlotRef(NamedTuple):
    """Reference objects used to update plots."""

    widget: weakref.ReferenceType[QtMplPlotCanvas]
    artists: list[weakref.ReferenceType[PathCollection]]

    def deref(self) -> tuple[QtMplPlotCanvas, list[PathCollection]]:
        """Dereference the weak references."""
        _widget = self.widget()
        _artists = [a() for a in self.artists]
        if _widget is None or None in _artists:
            raise RuntimeError("Widget and/or artists have been deleted")
        return _widget, _artists


@dataclass
class ScatterModel:
    ax: Axes
    x_selection: SelectionOperator | None
    y_selection: SelectionOperator
    table: TableBase
    label_selection: SelectionOperator | None = None
    alpha: float = 1.0
    ref: bool = False

    def add_data(self):
        _mpl_widget = weakref.ref(self.table.plt.gcw())
        _artist_refs: list[weakref.ReferenceType[PathCollection]] = []
        for x, y in self._iter_data():
            label_name = y.name

            artist = self.ax.scatter(
                x, y, alpha=self.alpha, label=label_name, picker=True
            )
            if not self.ref:
                # if plot does not refer the table data, there's nothing to be done
                return

            _artist_refs.append(weakref.ref(artist))

        plot_ref = PlotRef(_mpl_widget, _artist_refs)

        def _on_data_updated():
            # when any of the data is updated, reset the scatter offsets
            try:
                _plt, _artists = plot_ref.deref()
            except RuntimeError:
                updated = False
            else:
                updated = self.update_data(_artists, _plt)
            if not updated:
                self.table.events.data.disconnect(_on_data_updated)
                logger.debug("Disconnecting scatter plot.")

        reactive_ranges = self._get_reactive_ranges()
        self.table.events.data.mloc(reactive_ranges).connect(_on_data_updated)
        return None

    def update_data(
        self, artists: list[PathCollection], mpl_widget: QtMplPlotCanvas
    ) -> bool:
        """
        Update the data of the artist.
        Return True if the data is successfully updated.
        """
        try:
            for i, (x, y) in enumerate(self._iter_data()):
                artists[i].set_offsets(np.stack([x, y], axis=1))
            mpl_widget.draw()
        except RuntimeError as e:
            if str(e).startswith("wrapped C/C++ object of"):
                # Qt widget is deleted.
                return False

        return True

    def _get_reactive_ranges(self):
        data = self.table.data
        yslice = self.y_selection.as_iloc_slices(data)
        reactive_ranges = [yslice]

        if self.x_selection is not None:
            xslice = self.x_selection.as_iloc_slices(data)
            reactive_ranges.append(xslice)

        return reactive_ranges

    def _iter_data(self) -> Iterator[tuple[pd.Series, pd.Series]]:
        """Iterate over the data to be plotted."""
        data = self.table.data
        if self.y_selection is None:
            raise ValueError("Y must be set.")

        yslice = self.y_selection.as_iloc_slices(data)
        ydata_all = data.iloc[yslice]

        if self.x_selection is None:
            xdata = pd.Series(np.arange(len(ydata_all)), name="X")
        else:
            xdata = get_column(self.x_selection, data)

        if self.label_selection is None:
            for _, ydata in ydata_all.items():
                yield xdata, ydata
        else:
            ldata = get_column(self.label_selection, data)
            lable_unique = ldata.unique()

            for l in lable_unique:
                spec = ldata == l
                xdata_subset = xdata[spec]
                for _, ydata in ydata_all[spec].items():
                    yield xdata_subset, ydata


def get_column(selection: SelectionOperator, df: pd.DataFrame) -> pd.Series:
    sl = selection.as_iloc_slices(df)
    data = df.iloc[sl]
    if data.shape[1] != 1:
        raise ValueError("Label must be a single column.")
    return data.iloc[:, 0]
