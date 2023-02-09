from __future__ import annotations
from typing import Iterable, TYPE_CHECKING, Union
import numpy as np
from tabulous.color import ColorTuple, normalize_color
from tabulous.types import ColorType
from tabulous._dtype import isna, get_converter

if TYPE_CHECKING:
    from pandas.core.dtypes.dtypes import CategoricalDtype
    import pandas as pd

    _TimeLike = Union[pd.Timestamp, pd.Timedelta]
    _ColorType = tuple[int, int, int, int]

_DEFAULT_MIN = "#697FD1"
_DEFAULT_MAX = "#FF696B"


def exec_colormap_dialog(ds: pd.Series, parent=None):
    """Open a dialog to define a colormap for a series."""
    from tabulous._magicgui import ColorEdit
    from magicgui.widgets import Dialog, LineEdit, Container

    dtype = ds.dtype
    if dtype == "category":
        dtype: CategoricalDtype
        widgets = [
            ColorEdit(value=_random_color(), label=str(cat)) for cat in dtype.categories
        ]
        dlg = Dialog(widgets=widgets)
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            return dict(zip(dtype.categories, (w.value for w in widgets)))

    elif dtype.kind in "uif":  # unsigned int, int, float
        lmin = LineEdit(value=str(ds.min()))
        lmax = LineEdit(value=str(ds.max()))
        cmin = ColorEdit(value=_DEFAULT_MIN)
        cmax = ColorEdit(value=_DEFAULT_MAX)
        min_ = Container(
            widgets=[cmin, lmin], labels=False, layout="horizontal", label="Min"
        )
        min_.margins = (0, 0, 0, 0)
        max_ = Container(
            widgets=[cmax, lmax], labels=False, layout="horizontal", label="Max"
        )
        max_.margins = (0, 0, 0, 0)
        dlg = Dialog(widgets=[min_, max_])
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            return segment_by_float(
                [(float(lmin.value), cmin.value), (float(lmax.value), cmax.value)]
            )

    elif dtype.kind == "b":  # boolean
        false_ = ColorEdit(value=_DEFAULT_MIN, label="False")
        true_ = ColorEdit(value=_DEFAULT_MAX, label="True")
        dlg = Dialog(widgets=[false_, true_])
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            converter = get_converter(np.dtype(bool))
            _dict = {False: false_.value, True: true_.value}
            return lambda val: _dict.get(converter(val), None)

    elif dtype.kind in "mM":  # time stamp or time delta
        min_ = ColorEdit(value=_DEFAULT_MIN, label="Min")
        max_ = ColorEdit(value=_DEFAULT_MAX, label="Max")
        dlg = Dialog(widgets=[min_, max_])
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            return segment_by_time(
                [(ds.min(), min_.value), (ds.max(), max_.value)], dtype
            )

    else:
        raise NotImplementedError(
            f"Dtype {dtype!r} not supported. Please set colormap programmatically."
        )


def _random_color() -> list[int]:
    return list(np.random.randint(256, size=3)) + [255]


def _where(x, border: Iterable[float]) -> int:
    for i, v in enumerate(border):
        if x < v:
            return i - 1
    return len(border) - 1


def segment_by_float(maps: list[tuple[float, ColorType]]):
    converter = get_converter(np.dtype("f"))
    borders: list[float] = []
    colors: list[ColorTuple] = []
    for v, c in maps:
        borders.append(v)
        colors.append(normalize_color(c))
    idx_max = len(borders) - 1

    # check is sorted
    if not all(borders[i] <= borders[i + 1] for i in range(len(borders) - 1)):
        raise ValueError("Borders must be sorted")

    def _colormap(value: float) -> _ColorType:
        if isna(value):
            return None
        value = converter(value)
        idx = _where(value, borders)
        if idx == -1 or idx == idx_max:
            return colors[idx]
        min_color = np.array(colors[idx], dtype=np.float64)
        max_color = np.array(colors[idx + 1], dtype=np.float64)
        min = borders[idx]
        max = borders[idx + 1]
        return (value - min) / (max - min) * (max_color - min_color) + min_color

    return _colormap


def segment_by_time(maps: list[tuple[_TimeLike, ColorType]], dtype):
    converter = get_converter(dtype)
    borders: list[_TimeLike] = []
    colors: list[ColorTuple] = []
    for v, c in maps:
        borders.append(v)
        colors.append(normalize_color(c))
    idx_max = len(borders) - 1

    # check is sorted
    if not all(borders[i] <= borders[i + 1] for i in range(len(borders) - 1)):
        raise ValueError("Borders must be sorted")

    def _colormap(value: _TimeLike) -> _ColorType:
        if isna(value):
            return None
        value = converter(value)
        idx = _where(value, borders)
        if idx == -1 or idx == idx_max:
            return colors[idx]
        min_color = np.array(colors[idx], dtype=np.float64)
        max_color = np.array(colors[idx + 1], dtype=np.float64)
        min = borders[idx].value
        max = borders[idx + 1].value
        return (value.value - min) / (max - min) * (max_color - min_color) + min_color

    return _colormap
