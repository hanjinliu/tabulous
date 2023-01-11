from __future__ import annotations

from magicgui.widgets import Container, PushButton, DateTimeEdit, LineEdit, RadioButtons
from tabulous._magicgui import SelectionWidget

import pandas as pd


class DateRangeDialog(Container):
    def __init__(self):
        selection = SelectionWidget(
            format="iloc", allow_out_of_bounds=True, name="Selection"
        )
        start = DateTimeEdit(name="start")
        stop = DateTimeEdit(name="stop")
        method = RadioButtons(name="method", choices=["periods", "frequency"])
        periods = LineEdit(name="periods")
        freq = LineEdit(name="freq")
        call_btn = PushButton(text="Run")
        super().__init__(
            widgets=[selection, start, stop, method, periods, freq, call_btn]
        )
        self._selection = selection
        self._start = start
        self._stop = stop
        self._method = method
        self._periods = periods
        self._freq = freq
        self._call_btn = call_btn

        method.changed.connect(self._on_method_changed)
        self.called = self._call_btn.changed
        self.called.connect(self.close)

    def _on_method_changed(self, method: str):
        self._periods.visible = method == "periods"
        self._freq.visible = method == "frequency"

    def _on_called(self):
        self._selection.value.operate

    def get_value(self) -> pd.DatetimeIndex:
        start = self._start.value
        stop = self._stop.value
        if self._method.value == "periods":
            periods = self._periods.value
            freq = None
        else:
            periods = None
            freq = pd.to_timedelta(self._freq.value)
        data = pd.date_range(start=start, stop=stop, periods=periods, freq=freq)
        rsl, csl = self._selection.value.as_iloc_slices(None)
        if csl.start != csl.stop - 1:
            raise ValueError("Selection must be a single column")
        return self._selection.value.operate(data)
