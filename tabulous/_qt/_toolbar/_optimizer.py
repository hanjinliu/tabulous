from typing import TYPE_CHECKING
from scipy import optimize as sp_opt
import numpy as np
import pandas as pd
from magicgui.widgets import Container, ComboBox, CheckBox, PushButton

from ..._selection_op import SelectionOperator
from ..._magicgui import find_current_table, SelectionWidget

if TYPE_CHECKING:
    from .._table._base import QMutableSimpleTable


class OptimizerWidget(Container):
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
        self._refresh_checkbox = CheckBox(
            value=True, label="Update during optimization"
        )
        self._call_button = PushButton(text="Run", tooltip="Run optimization")
        self._call_button.changed.connect(self._on_called)
        super().__init__(
            widgets=[
                self._cost_selector,
                self._param_selector,
                self._minimize_cbox,
                self._refresh_checkbox,
                self._call_button,
            ]
        )

    def _on_called(self):
        self.optimize(
            cost=self._cost_selector.value,
            parameters=self._param_selector.value,
            minimize=self._minimize_cbox.value == "minimize",
            refresh=self._refresh_checkbox.value,
        )

    def optimize(
        self,
        cost: SelectionOperator,
        parameters: SelectionOperator,
        minimize: bool = True,
        refresh: bool = True,
    ):
        table = find_current_table(self)
        df = table.data_shown
        dst = cost.as_iat(df)
        params = parameters.as_iloc_slices(df)
        return _optimize_in_table(table._qwidget, dst, params, minimize, refresh)

    @classmethod
    def new(cls) -> "OptimizerWidget":
        if cls._current_widget is None:
            cls._current_widget = cls()
        return cls._current_widget


def _optimize_in_table(
    table: "QMutableSimpleTable",
    dst: tuple[int, int],
    params: tuple[slice, slice],
    minimize: bool = True,
    refresh: bool = True,
):
    # TODO: merge command

    if dst not in table._qtable_view._ref_graphs:
        raise ValueError(f"{dst} has no reference.")

    if minimize:
        cost_function = _get_minimize_target(table, dst, params)
    else:
        cost_function = _get_maximize_target(table, dst, params)

    data = table.dataShown().iloc[params]
    param0 = data.to_numpy(dtype=np.float64, copy=False)

    if refresh:
        callback = lambda x: table.refreshTable(True)
    else:
        callback = None
    return sp_opt.minimize(cost_function, param0, callback=callback)


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
