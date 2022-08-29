from __future__ import annotations
from typing import Callable
import numpy as np
import pandas as pd

_ColorType = tuple[int, int, int, int]


def exec_colormap_dialog(ds: pd.Series, parent=None) -> Callable | None:
    from ..._color_edit import ColorEdit
    from magicgui.widgets import Dialog

    if ds.dtype.kind in "uif":
        min_ = ColorEdit(value="blue")
        max_ = ColorEdit(value="red")
        dlg = Dialog(widgets=[min_, max_])
        dlg.native.setParent(parent, dlg.native.windowFlags())
        if dlg.exec():
            return _define_colormap(ds.min(), ds.max(), min_.value, max_.value)
    return None


def _define_colormap(
    min: float, max: float, min_color: _ColorType, max_color: _ColorType
):
    def _colormap(value: float) -> _ColorType:
        nonlocal min_color, max_color
        if pd.isna(value):
            return None
        elif value < min:
            return min_color
        elif value > max:
            return max_color
        else:
            min_color = np.array(min_color, dtype=np.float64)
            max_color = np.array(max_color, dtype=np.float64)
            return (value - min) / (max - min) * (max_color - min_color) + min_color

    return _colormap
