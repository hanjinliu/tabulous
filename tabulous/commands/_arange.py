from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any
from datetime import datetime, timedelta
from psygnal import Signal
from magicgui.widgets import (
    Container,
    PushButton,
    DateTimeEdit,
    LineEdit,
    ComboBox,
)
from tabulous._magicgui import SelectionWidget, TimeDeltaEdit

import pandas as pd

if TYPE_CHECKING:
    from magicgui.widgets.bases import ValueWidget


class _CheckedWidget(Container):
    check_changed = Signal(bool)

    def __init__(self, widget: ValueWidget, checked: bool = True, **kwargs):
        from tabulous._magicgui import ToggleSwitch

        self._cbox = ToggleSwitch(value=checked)
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


class _RangeDialog(Container):
    def __init__(self):
        selection = SelectionWidget(
            format="iloc", allow_out_of_bounds=True, name="Selection"
        )
        start, end = self._prep_start_and_end()
        start = _CheckedWidget(start)
        end = _CheckedWidget(end)
        freq = _CheckedWidget(self._prep_freq(), checked=False, enabled=False)

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

    def _prep_start_and_end(self) -> tuple[_CheckedWidget, _CheckedWidget]:
        raise NotImplementedError()

    def _prep_freq(self) -> _CheckedWidget:
        raise NotImplementedError()

    def get_range(self, start=None, end=None, periods=None, freq=None):
        raise NotImplementedError()

    def _get_params(self):
        start = self._start.value if self._start.checked else None
        end = self._end.value if self._end.checked else None
        freq = self._freq.value if self._freq.checked else None
        return start, end, freq

    def get_value(self, df: pd.DataFrame) -> tuple[slice, slice, pd.Index]:
        rsl, csl = self._selection.value.as_iloc_slices(df)
        if csl.start != csl.stop - 1:
            raise ValueError("Selection must be a single column")
        periods = rsl.stop - rsl.start
        start, end, freq = self._get_params()
        data = self.get_range(start=start, end=end, periods=periods, freq=freq)
        return rsl, csl, data


class _TimeRangeDialog(_RangeDialog):
    def _prep_freq(self) -> _CheckedWidget:
        return TimeDeltaEdit(name="freq", value=timedelta(days=1))


class DateRangeDialog(_TimeRangeDialog):
    def _prep_start_and_end(self):
        start = DateTimeEdit(name="start", value=datetime(2000, 1, 1))
        end = DateTimeEdit(name="stop", value=datetime(2000, 12, 31))
        return start, end

    def get_range(self, start=None, end=None, periods=None, freq=None):
        return pd.date_range(start=start, end=end, periods=periods, freq=freq)


class TimeDeltaRangeDialog(_TimeRangeDialog):
    def _prep_start_and_end(self):
        start = TimeDeltaEdit(name="start", value=timedelta(seconds=0))
        end = TimeDeltaEdit(name="stop", value=timedelta(seconds=60))
        return start, end

    def get_range(self, start=None, end=None, periods=None, freq=None):
        return pd.timedelta_range(start=start, end=end, periods=periods, freq=freq)


class PeriodRangeDialog(_TimeRangeDialog):
    def _prep_start_and_end(self):
        start = DateTimeEdit(name="start", value=datetime(2000, 1, 1))
        end = DateTimeEdit(name="stop", value=datetime(2000, 12, 31))
        return start, end

    def _prep_freq(self) -> _CheckedWidget:
        return LineEdit(name="freq", value="1d", tooltip="Period frequency")

    def get_range(self, start=None, end=None, periods=None, freq=None):
        return pd.period_range(start=start, end=end, periods=periods, freq=freq)


class IntervalRangeDialog(_RangeDialog):
    def __init__(self):
        super().__init__()
        self._closed = ComboBox(
            choices=[
                ("[a, b)", "left"),
                ("(a, b]", "right"),
                ("[a, b]", "both"),
                ("(a, b)", "neither"),
            ],
            name="close_state",
        )

    def _prep_start_and_end(self):
        start = LineEdit(name="start", value="0.0")
        end = LineEdit(name="stop", value="1.0")
        return start, end

    def _prep_freq(self):
        return LineEdit(name="freq", value="0.1")

    def get_range(self, start=None, end=None, periods=None, freq=None):
        return pd.interval_range(
            start=ast.literal_eval(start) if start is not None else None,
            end=ast.literal_eval(end) if end is not None else None,
            periods=periods,
            freq=ast.literal_eval(freq) if freq is not None else None,
            closed=self._closed.value,
        )
