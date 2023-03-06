from __future__ import annotations

from enum import Enum
import numpy as np
import pandas as pd
from psygnal import Signal
from magicgui.widgets import Container, ComboBox, PushButton
from tabulous._magicgui import SelectionWidget, find_current_table


class Formula(Enum):
    linear = "linear"
    quadratic = "quadratic"
    cubic = "cubic"


_EXPRESSION = {
    Formula.linear: "y = ax + b",
    Formula.quadratic: "y = ax<sup>2</sup> + bx + c",
    Formula.cubic: "y = ax<sup>3</sup> + bx<sup>2</sup> + cx + d",
}


class PolynomialFitWidget(Container):
    called = Signal(pd.Series)

    def __init__(self):
        self._xrange = SelectionWidget(label="X")
        self._yrange = SelectionWidget(label="Y")
        self._formula = ComboBox(
            choices=[(_EXPRESSION[k], k) for k in Formula], label="Formula"
        )
        self._btn = PushButton(text="Fit")
        self._btn.changed.connect(self.fit)

        widgets = [self._xrange, self._yrange, self._formula, self._btn]
        super().__init__(widgets=widgets)

    def _get_xy(self) -> tuple[np.ndarray, np.ndarray]:
        table = find_current_table(self)
        df = table.data
        x = self._xrange.value.operate(df)
        y = self._yrange.value.operate(df)
        if 1 in x.shape and 1 in y.shape:
            return x.values.ravel(), y.values.ravel()
        raise ValueError("X and Y must be 1D array")

    def fit(self):
        x, y = self._get_xy()
        if self._formula.value is Formula.linear:
            df = self._fit_linear(x, y)
        elif self._formula.value is Formula.quadratic:
            df = self._fit_quadratic(x, y)
        elif self._formula.value is Formula.cubic:
            df = self._fit_cubic(x, y)
        else:
            raise RuntimeError("Unknown formula")
        self.close()
        self.called.emit(df)

    def _fit_linear(self, x: np.ndarray, y: np.ndarray):
        coef, (res, *_) = np.polynomial.polynomial.polyfit(x, y, 1, full=True)
        return pd.DataFrame(
            [[coef[1]], [coef[0]], [res[0]]],
            index=["a", "b", "residual"],
            columns=["result"],
        )

    def _fit_quadratic(self, x: np.ndarray, y: np.ndarray):
        coef, (res, *_) = np.polynomial.polynomial.polyfit(x, y, 2, full=True)
        return pd.DataFrame(
            [[coef[2]], [coef[1]], [coef[0]], [res[0]]],
            index=["a", "b", "c", "residual"],
            columns=["result"],
        )

    def _fit_cubic(self, x: np.ndarray, y: np.ndarray):
        coef, (res, *_) = np.polynomial.polynomial.polyfit(x, y, 3, full=True)
        return pd.DataFrame(
            [[coef[3]], [coef[2]], [coef[1]], [coef[0]], [res[0]]],
            index=["a", "b", "c", "d", "residual"],
            columns=["result"],
        )
