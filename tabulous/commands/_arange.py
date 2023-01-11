from __future__ import annotations

from typing import TYPE_CHECKING, Any
from datetime import datetime, timedelta
from psygnal import Signal
from magicgui.widgets import Container, PushButton, DateTimeEdit, CheckBox
from tabulous._magicgui import SelectionWidget, TimeDeltaEdit

import pandas as pd

if TYPE_CHECKING:
    from magicgui.widgets.bases import ValueWidget


class _CheckedWidget(Container):
    check_changed = Signal(bool)

    def __init__(self, widget: ValueWidget, checked: bool = True, **kwargs):
        self._cbox = CheckBox(value=checked)
        self._cbox.max_width = 28
        self._child_widget = widget
        super().__init__(
            widgets=[self._cbox, widget],
            layout="horizontal",
            labels=False,
            name=widget.name,
            label=widget.label,
            **kwargs,
        )
        self.margins = (0, 0, 0, 0)
        self._cbox.changed.connect(self.check_changed.emit)

    @property
    def value(self) -> Any:
        return self._child_widget.value

    @value.setter
    def value(self, val):
        self._child_widget.value = val

    @property
    def checked(self):
        return self._cbox.value

    @checked.setter
    def checked(self, val):
        self._cbox.value = val


class DateRangeDialog(Container):
    def __init__(self):
        selection = SelectionWidget(
            format="iloc", allow_out_of_bounds=True, name="Selection"
        )
        start = _CheckedWidget(DateTimeEdit(name="start", value=datetime(2000, 1, 1)))
        end = _CheckedWidget(DateTimeEdit(name="stop", value=datetime(2000, 12, 31)))
        freq = _CheckedWidget(
            TimeDeltaEdit(name="freq", value=timedelta(days=1)),
            checked=False,
            enabled=False,
        )

        start.check_changed.connect(lambda: self._on_check_state_changed(start))
        end.check_changed.connect(lambda: self._on_check_state_changed(end))
        freq.check_changed.connect(lambda: self._on_check_state_changed(freq))
        call_btn = PushButton(text="Run")
        super().__init__(widgets=[selection, start, end, freq, call_btn])
        self._selection = selection
        self._start = start
        self._end = end
        self._freq = freq
        self._call_btn = call_btn

        self.called = self._call_btn.changed
        self.called.connect(self.close)

    def _on_check_state_changed(self, widget: _CheckedWidget):
        for _w in (self._start, self._end, self._freq):
            if _w is widget:
                assert not _w.checked
            else:
                with _w.check_changed.blocked():
                    _w.checked = True
            _w.enabled = _w.checked

    def get_value(self, df: pd.DataFrame) -> tuple[slice, slice, pd.DatetimeIndex]:
        rsl, csl = self._selection.value.as_iloc_slices(df)
        if csl.start != csl.stop - 1:
            raise ValueError("Selection must be a single column")
        periods = rsl.stop - rsl.start
        start = self._start.value if self._start.checked else None
        end = self._end.value if self._end.checked else None
        freq = self._freq.value if self._freq.checked else None
        data = pd.date_range(start=start, end=end, periods=periods, freq=freq)
        return rsl, csl, data
