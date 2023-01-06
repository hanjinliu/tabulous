from __future__ import annotations
from typing import Callable, Hashable, Sequence, TYPE_CHECKING, TypeVar
import numpy as np
import pandas as pd
from tabulous._dtype import isna, get_converter

if TYPE_CHECKING:
    from pandas.core.dtypes.dtypes import CategoricalDtype


_ColorType = tuple[int, int, int, int]
_DEFAULT_MIN = "#697FD1"
_DEFAULT_MAX = "#FF696B"


def exec_colormap_dialog(ds: pd.Series, parent=None) -> Callable | None:
    """Open a dialog to define a colormap for a series."""
    from tabulous._qt._color_edit import ColorEdit
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
            return _define_categorical_colormap(
                dtype.categories,
                [w.value for w in widgets],
                dtype.kind,
            )

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
            return _define_continuous_colormap(
                float(lmin.value), float(lmax.value), cmin.value, cmax.value
            )

    elif dtype.kind == "b":  # boolean
        false_ = ColorEdit(value=_DEFAULT_MIN, label="False")
        true_ = ColorEdit(value=_DEFAULT_MAX, label="True")
        dlg = Dialog(widgets=[false_, true_])
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            return _define_categorical_colormap(
                [False, True], [false_.value, true_.value], dtype.kind
            )

    elif dtype.kind in "mM":  # time stamp or time delta
        min_ = ColorEdit(value=_DEFAULT_MIN, label="Min")
        max_ = ColorEdit(value=_DEFAULT_MAX, label="Max")
        dlg = Dialog(widgets=[min_, max_])
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            return _define_time_colormap(
                ds.min(), ds.max(), min_.value, max_.value, dtype.kind
            )

    else:
        raise NotImplementedError(
            f"Dtype {dtype!r} not supported. Please set colormap programmatically."
        )

    return None


def _define_continuous_colormap(
    min: float, max: float, min_color: _ColorType, max_color: _ColorType
):
    converter = get_converter("f")

    def _colormap(value: float) -> _ColorType:
        nonlocal min_color, max_color
        if isna(value):
            return None
        value = converter(value)
        if value < min:
            return min_color
        elif value > max:
            return max_color
        else:
            min_color = np.array(min_color, dtype=np.float64)
            max_color = np.array(max_color, dtype=np.float64)
            return (value - min) / (max - min) * (max_color - min_color) + min_color

    return _colormap


def _define_categorical_colormap(
    values: Sequence[Hashable],
    colors: Sequence[_ColorType],
    kind: str,
):
    map = dict(zip(values, colors))
    converter = get_converter(kind)

    def _colormap(value: Hashable) -> _ColorType:
        return map.get(converter(value), None)

    return _colormap


_T = TypeVar("_T", pd.Timestamp, pd.Timedelta)


def _define_time_colormap(
    min: _T,
    max: _T,
    min_color: _ColorType,
    max_color: _ColorType,
    kind: str,
):
    min_t = min.value
    max_t = max.value
    converter = get_converter(kind)

    def _colormap(value: _T) -> _ColorType:
        nonlocal min_color, max_color
        if isna(value):
            return None
        value = converter(value).value
        if value < min_t:
            return min_color
        elif value > max_t:
            return max_color
        else:
            min_color = np.array(min_color, dtype=np.float64)
            max_color = np.array(max_color, dtype=np.float64)
            return (value - min_t) / (max_t - min_t) * (
                max_color - min_color
            ) + min_color

    return _colormap


def _random_color() -> list[int]:
    return list(np.random.randint(256, size=3)) + [255]
