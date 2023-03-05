from typing import TYPE_CHECKING
from scipy import optimize as sp_opt
import numpy as np
import pandas as pd
from magicgui.widgets import Container, ComboBox, PushButton, SpinBox

from tabulous._magicgui import find_current_table, SelectionWidget

if TYPE_CHECKING:
    from tabulous._qt._table._base import QMutableSimpleTable


class OptimizerWidget(Container):
    """A widget for Excel's solver-like optimization."""

    _current_widget = None

    def __init__(self):
        self._cost_selector = SelectionWidget(
            label="Cost", tooltip="Select the cost cell"
        )
        self._param_selector = SelectionWidget(
            label="Parameters", tooltip="Select the parameter cells"
        )
        self._minimize_cbox = ComboBox(
            label="Optimize by", choices=["minimize", "maximize"]
        )
        self._maxiter = SpinBox(value=50, label="Max Iterations")

        self._call_button = PushButton(text="Run", tooltip="Run optimization")
        super().__init__(
            widgets=[
                self._cost_selector,
                self._param_selector,
                self._minimize_cbox,
                self._maxiter,
                self._call_button,
            ]
        )
        self._call_button.changed.connect(self._on_called)

    def _on_called(self):
        table = find_current_table(self)
        df = table.data_shown
        dst = self._cost_selector.value.as_iat(df)
        params = self._param_selector.value.as_iloc_slices(df)
        qtable = table._qwidget
        if dst not in qtable._qtable_view._table_map:
            raise ValueError(f"{dst} has no reference.")

        if self._minimize_cbox.value == "minimize":
            cost_function = _get_minimize_target(qtable, dst, params)
        else:
            cost_function = _get_maximize_target(qtable, dst, params)

        data = qtable.dataShown().iloc[params]
        param0 = data.to_numpy(dtype=np.float64, copy=False)

        def callback(x):
            return qtable.refreshTable(True)

        with qtable._mgr.merging(lambda x: "optimize"):
            sp_opt.minimize(
                cost_function,
                param0,
                callback=callback,
                options=dict(maxiter=self._maxiter.value),
            )
        return None

    @classmethod
    def new(cls) -> "OptimizerWidget":
        if cls._current_widget is None:
            cls._current_widget = cls()
        return cls._current_widget


def _get_minimize_target(
    table: "QMutableSimpleTable", dst: tuple[int, int], params: tuple[slice, slice]
):
    def cost_func(p):
        table.setDataFrameValue(*params, pd.DataFrame(p))
        val = table.dataShown().iat[dst]
        return float(val)

    return cost_func


def _get_maximize_target(
    table: "QMutableSimpleTable", dst: tuple[int, int], params: tuple[slice, slice]
):
    def cost_func(p):
        table.setDataFrameValue(*params, pd.DataFrame(p))
        val = table.dataShown().iat[dst]
        return -float(val)

    return cost_func
