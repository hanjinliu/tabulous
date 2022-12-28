from __future__ import annotations
from typing import Iterator, TYPE_CHECKING, NamedTuple, Generic, TypeVar, Union
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
    from matplotlib.artist import Artist
    from matplotlib.collections import PathCollection, PolyCollection
    from matplotlib.lines import Line2D
    from matplotlib.patches import Polygon
    from matplotlib.container import BarContainer
    from tabulous._qt._plot import QtMplPlotCanvas

logger = logging.getLogger(__name__)
_T = TypeVar("_T", bound="Artist")


class PlotRef(NamedTuple):
    """Reference objects used to update plots."""

    widget: weakref.ReferenceType[QtMplPlotCanvas]
    artists: list[weakref.ReferenceType[Artist]]

    def deref(self) -> tuple[QtMplPlotCanvas, list[Artist]]:
        """Dereference the weak references."""
        _widget = self.widget()
        _artists = [a() for a in self.artists]
        if _widget is None or None in _artists:
            raise RuntimeError("Widget and/or artists have been deleted")
        return _widget, _artists


class AbstractDataModel(Generic[_T]):
    ax: Axes
    table: TableBase
    ref = False

    def update_ax(self, *args, **kwargs) -> _T:
        raise NotImplementedError()

    def update_artist(self, artist: _T, *args: pd.Series):
        raise NotImplementedError()

    def add_data(self):
        raise NotImplementedError()

    def update_data(self, artists: list[_T], mpl_widget: QtMplPlotCanvas) -> bool:
        """
        Update the data of the artist.
        Return True if the data is successfully updated.
        """
        try:
            for i, data in enumerate(self._iter_data()):
                self.update_artist(artists[i], *data)
            mpl_widget.draw()
        except RuntimeError as e:
            if str(e).startswith("wrapped C/C++ object of"):
                # Qt widget is deleted.
                return False

        return True

    def _get_reactive_ranges(self) -> list[tuple[slice, slice]]:
        raise NotImplementedError()

    def _iter_data(self) -> Iterator[tuple[pd.Series, ...]]:
        """Iterate over the data to be plotted."""
        raise NotImplementedError()


class YDataModel(AbstractDataModel[_T]):
    ax: Axes
    y_selection: SelectionOperator
    table: TableBase

    label_selection = None  # default
    ref = False

    def add_data(self):
        _mpl_widget = weakref.ref(self.table.plt.gcw())
        _artist_refs: list[weakref.ReferenceType[_T]] = []
        for (y,) in self._iter_data():
            label_name = y.name
            artist = self.update_ax(y, label=label_name)
            # _artist_refs.append(weakref.ref(artist))  TODO: cannot weakref BarContainer

        if not self.ref:
            # if plot does not refer the table data, there's nothing to be done
            return

        # NOTE: Unreachable below
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

    def _get_reactive_ranges(self) -> list[tuple[slice, slice]]:
        data = self.table.data
        yslice = self.y_selection.as_iloc_slices(data)
        reactive_ranges = [yslice]
        return reactive_ranges

    def _iter_data(self) -> Iterator[tuple[pd.Series]]:
        """Iterate over the data to be plotted."""
        data = self.table.data
        if self.y_selection is None:
            raise ValueError("Y must be set.")

        yslice = self.y_selection.as_iloc_slices(data)
        ydata_all = data.iloc[yslice]

        if self.label_selection is None:
            for _, ydata in ydata_all.items():
                yield (ydata,)
        else:
            ldata = get_column(self.label_selection, data)
            lable_unique = ldata.unique()

            for l in lable_unique:
                spec = ldata == l
                for _, ydata in ydata_all[spec].items():
                    yield (ydata,)


class XYDataModel(AbstractDataModel[_T]):
    ax: Axes
    x_selection: SelectionOperator | None
    y_selection: SelectionOperator
    table: TableBase

    label_selection = None  # default
    ref = False

    def add_data(self):
        _mpl_widget = weakref.ref(self.table.plt.gcw())
        _artists: list[_T] = []
        for x, y in self._iter_data():
            label_name = y.name
            artist = self.update_ax(x, y, label=label_name)
            _artists.append(artist)

        if not self.ref:
            # if plot does not refer the table data, there's nothing to be done
            return

        _artist_refs: list[weakref.ReferenceType[_T]] = []
        for artist in _artists:
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

    def _get_reactive_ranges(self) -> list[tuple[slice, slice]]:
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
        # TODO: support row vector
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


class XYYDataModel(AbstractDataModel[_T]):
    ax: Axes
    x_selection: SelectionOperator | None
    y0_selection: SelectionOperator
    y1_selection: SelectionOperator
    table: TableBase

    label_selection = None  # default
    ref = False

    def add_data(self):
        _mpl_widget = weakref.ref(self.table.plt.gcw())
        _artists: list[_T] = []
        for x, y0, y1 in self._iter_data():
            label_name = y0.name
            artist = self.update_ax(x, y0, y1, label=label_name)
            _artists.append(artist)

        if not self.ref:
            # if plot does not refer the table data, there's nothing to be done
            return

        _artist_refs: list[weakref.ReferenceType[_T]] = []
        for artist in _artists:
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

    def _get_reactive_ranges(self) -> list[tuple[slice, slice]]:
        data = self.table.data
        y0slice = self.y0_selection.as_iloc_slices(data)
        y1slice = self.y1_selection.as_iloc_slices(data)
        reactive_ranges = [y0slice, y1slice]

        if self.x_selection is not None:
            xslice = self.x_selection.as_iloc_slices(data)
            reactive_ranges.append(xslice)

        return reactive_ranges

    def _iter_data(self) -> Iterator[tuple[pd.Series, pd.Series, pd.Series]]:
        """Iterate over the data to be plotted."""
        data = self.table.data
        if self.y0_selection is None or self.y1_selection is None:
            raise ValueError("Y0 and Y1 must be set.")

        y0data = get_column(self.y0_selection, data)
        y1data = get_column(self.y1_selection, data)
        if len(y0data) != len(y1data):
            raise ValueError("Y0 and Y1 must have the same length.")
        if self.x_selection is None:
            xdata = pd.Series(np.arange(len(y0data)), name="X")
        else:
            xdata = get_column(self.x_selection, data)

        if self.label_selection is None:
            yield xdata, y0data, y1data
        else:
            ldata = get_column(self.label_selection, data)
            lable_unique = ldata.unique()

            for l in lable_unique:
                spec = ldata == l
                xdata_subset = xdata[spec]
                yield xdata_subset, y0data[spec], y1data[spec]


@dataclass
class PlotModel(XYDataModel["Line2D"]):
    ax: Axes
    x_selection: SelectionOperator | None
    y_selection: SelectionOperator
    table: TableBase
    alpha: float = 1.0
    ref: bool = False

    def update_ax(self, x, y, label=None) -> Line2D:
        return self.ax.plot(x, y, alpha=self.alpha, label=label, picker=True)[0]

    def update_artist(self, artist: Line2D, x: pd.Series, y: pd.Series):
        return artist.set_data(x, y)


@dataclass
class BarModel(XYDataModel["BarContainer"]):
    ax: Axes
    x_selection: SelectionOperator | None
    y_selection: SelectionOperator
    table: TableBase
    alpha: float = 1.0
    ref: bool = False

    def update_ax(self, x, y, label=None) -> BarContainer:
        return self.ax.bar(x, y, alpha=self.alpha, label=label, picker=True)

    def update_artist(self, artist: BarContainer, x: pd.Series, y: pd.Series):
        for patch in artist.patches:
            width = patch.get_width()
            patch.set_x(x - width / 2)
            patch.set_height(y)
        return None


@dataclass
class FillBetweenModel(XYYDataModel["PolyCollection"]):
    ax: Axes
    x_selection: SelectionOperator | None
    y0_selection: SelectionOperator
    y1_selection: SelectionOperator
    table: TableBase
    alpha: float = 1.0
    ref: bool = False

    def update_ax(self, x, y0, y1, label=None) -> PolyCollection:
        return self.ax.fill_between(
            x, y0, y1, alpha=self.alpha, label=label, picker=True
        )

    def update_artist(
        self, artist: PolyCollection, x: pd.Series, y0: pd.Series, y1: pd.Series
    ):
        new_verts = np.concatenate(
            [np.stack([x, y0], axis=1), np.stack([x, y1], axis=1)[::-1]],
            axis=0,
        )
        artist.set_verts(new_verts[np.newaxis])
        return None


@dataclass
class FillBetweenXModel(FillBetweenModel):
    def update_ax(self, x, y0, y1, label=None) -> PolyCollection:
        return self.ax.fill_betweenx(
            x, y0, y1, alpha=self.alpha, label=label, picker=True
        )

    def update_artist(
        self, artist: PolyCollection, x: pd.Series, y0: pd.Series, y1: pd.Series
    ):
        new_verts = np.concatenate(
            [np.stack([y0, x], axis=1), np.stack([y1, x], axis=1)[::-1]],
            axis=0,
        )
        artist.set_verts(new_verts[np.newaxis])
        return None


@dataclass
class ScatterModel(XYDataModel["PathCollection"]):
    ax: Axes
    x_selection: SelectionOperator | None
    y_selection: SelectionOperator
    table: TableBase
    label_selection: SelectionOperator | None = None
    alpha: float = 1.0
    ref: bool = False

    def update_ax(self, x, y, label=None) -> PathCollection:
        return self.ax.scatter(x, y, alpha=self.alpha, label=label, picker=True)

    def update_artist(self, artist: PathCollection, x: pd.Series, y: pd.Series):
        return artist.set_offsets(np.stack([x, y], axis=1))


@dataclass
class HistModel(YDataModel[Union["BarContainer", "Polygon"]]):
    ax: Axes
    y_selection: SelectionOperator
    bins: int
    table: TableBase
    range: tuple[float, float] | None = None
    label_selection: SelectionOperator | None = None
    alpha: float = 1.0
    density: bool = False
    histtype: str = "bar"
    ref: bool = False

    def update_ax(self, y, label=None) -> Union[BarContainer, Polygon]:
        artist = self.ax.hist(
            y,
            alpha=self.alpha,
            label=label,
            bins=self.bins,
            density=self.density,
            range=self.range,
            histtype=self.histtype,
            picker=True,
        )[2]
        if self.histtype in ("step", "stepfilled"):
            return artist[0]
        else:
            return artist

    def update_artist(self, artist: Union[BarContainer, Polygon], y: pd.Series):
        raise NotImplementedError()


def get_column(selection: SelectionOperator, df: pd.DataFrame) -> pd.Series:
    sl = selection.as_iloc_slices(df)
    data = df.iloc[sl]
    if data.shape[1] != 1:
        raise ValueError("Label must be a single column.")
    return data.iloc[:, 0]
