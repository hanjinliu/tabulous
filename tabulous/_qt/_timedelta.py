from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Union
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Signal

_TimeDeltaLike = Union[datetime.timedelta, str, int, float]


class Section:
    NONE = -1
    DAY = 0
    HOUR = 1
    MINUTE = 2
    SECOND = 3


class QTimeDeltaEdit(QtW.QAbstractSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = datetime.timedelta(0)
        self._min = datetime.timedelta(-999999999)
        self._max = datetime.timedelta(999999999)
        self._step = datetime.timedelta(seconds=1)
        self.setLineEdit(_QTimeDeltaLineEdit(self._value, self))
        self.lineEdit().timedeltaChanged.connect(self.setValue)
        self.lineEdit().sectionChanged.connect(self._on_section_changed)
        self.setMinimumHeight(self.lineEdit().minimumHeight())

    if TYPE_CHECKING:

        def lineEdit(self) -> _QTimeDeltaLineEdit:
            ...

    def value(self) -> datetime.timedelta:
        return self._value

    def setValue(self, value: _TimeDeltaLike) -> None:
        self._value = to_timedelta(value)
        if self._min <= self._value <= self._max:
            self._update_text(self._value)
            self.update()
            return None
        raise ValueError(f"{value} is out of bound.")

    def singleStep(self) -> datetime.timedelta:
        return self._step

    def setSingleStep(self, step: _TimeDeltaLike):
        self._step = to_timedelta(step)

    def stepBy(self, steps: int) -> None:
        """Increment/decrement the time delta by the step value."""
        line = self.lineEdit()
        start = line.selectionStart()
        length = line.selectionLength()
        self.setValue(self.value() + steps * self.singleStep())
        line.setSelection(start, length)

    def maximum(self) -> datetime.timedelta:
        return self._max

    def setMaximum(self, max: _TimeDeltaLike) -> None:
        self._max = to_timedelta(max)

    def minimum(self) -> datetime.timedelta:
        return self._min

    def setMinimum(self, min: _TimeDeltaLike) -> None:
        self._min = to_timedelta(min)

    def setRange(self, min: _TimeDeltaLike, max: _TimeDeltaLike):
        self.setMinimum(min)
        self.setMaximum(max)

    def stepEnabled(self):
        flags = QtW.QAbstractSpinBox.StepEnabledFlag.StepNone
        if self.isReadOnly():
            return flags
        if self._value < self._max:
            flags |= QtW.QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
        if self._value > self._min:
            flags |= QtW.QAbstractSpinBox.StepEnabledFlag.StepDownEnabled
        return flags

    def sizeHint(self):
        # copied from superqt.QLargeIntSpinBox
        self.ensurePolished()
        fm = QtGui.QFontMetrics(self.font())
        h = self.lineEdit().sizeHint().height()
        if hasattr(fm, "horizontalAdvance"):
            # Qt >= 5.11
            w = fm.horizontalAdvance(str(self._value)) + 3
        else:
            w = fm.width(str(self._value)) + 3
        w = max(36, w)
        opt = QtW.QStyleOptionSpinBox()
        self.initStyleOption(opt)
        hint = QtCore.QSize(w, h)
        return self.style().sizeFromContents(
            QtW.QStyle.ContentsType.CT_SpinBox, opt, hint, self
        )

    def _update_text(self, value: datetime.timedelta) -> None:
        self.lineEdit().setTimedelta(value, emit=False)

    def _on_section_changed(self, section: int) -> None:
        if section == Section.SECOND:
            self.setSingleStep(datetime.timedelta(seconds=1))
        elif section == Section.MINUTE:
            self.setSingleStep(datetime.timedelta(minutes=1))
        elif section == Section.HOUR:
            self.setSingleStep(datetime.timedelta(hours=1))
        elif section == Section.DAY:
            self.setSingleStep(datetime.timedelta(days=1))
        self.lineEdit()._select_section(section)


class _QTimeDeltaLineEdit(QtW.QLineEdit):
    sectionChanged = Signal(int)  # position
    timedeltaChanged = Signal(datetime.timedelta)

    def __init__(self, value: datetime.timedelta, parent=None):
        super().__init__(parent)
        self.setTimedelta(value)
        # "000 days 00:00:00" format
        self.setInputMask(r"###0\ \d\ays\ 00\:00\:00")
        self.cursorPositionChanged.connect(self._on_cursor_position_changed)

    def timedelta(self) -> datetime.timedelta:
        days, rest = self.text().split("days")
        hours, mins, secs = rest.split(":")
        days, hours, mins, secs = map(int, (days, hours, mins, secs))
        return datetime.timedelta(days, hours * 3600 + mins * 60 + secs)

    def setTimedelta(self, value: datetime.timedelta, emit=True) -> None:
        days = value.days
        sec_tot = value.seconds
        hours, min_rest = divmod(sec_tot, 3600)
        mins, secs = divmod(min_rest, 60)
        text = f"{days: 3} days {hours:02}:{mins:02}:{secs:02}"
        self.setText(text)
        if emit:
            self.timedeltaChanged.emit(value)

    def event(self, a0: QtCore.QEvent) -> bool:
        _type = a0.type()
        if _type == QtCore.QEvent.Type.Wheel:
            e = QtGui.QWheelEvent(a0)
            pos = self.cursorPositionAt(e.pos())
            self.sectionChanged.emit(self.sectionUnderCursor(pos))
            return True

        return super().event(a0)

    def sectionUnderCursor(self, pos: int) -> int:
        # nchar = 18
        if 16 <= pos:
            return Section.SECOND
        elif 13 <= pos:
            return Section.MINUTE
        elif 10 <= pos:
            return Section.HOUR
        else:
            return Section.DAY

    def _select_section(self, section: int) -> None:
        if section == Section.SECOND:
            self.setSelection(16, 2)
        elif section == Section.MINUTE:
            self.setSelection(13, 2)
        elif section == Section.HOUR:
            self.setSelection(10, 2)
        else:
            self.setSelection(1, 3)

    def _on_cursor_position_changed(self, old: int, new: int) -> None:
        section_old = self.sectionUnderCursor(old)
        section_new = self.sectionUnderCursor(new)
        if section_old != section_new:
            self.sectionChanged.emit(section_new)


def to_timedelta(value: _TimeDeltaLike) -> datetime.timedelta:
    if not isinstance(value, datetime.timedelta):
        import pandas as pd

        pd_td = pd.to_timedelta(value)
        if isinstance(pd_td, pd.Timedelta):
            value = pd_td.to_pytimedelta()
        else:
            raise TypeError(f"Cannot convert {value} to timedelta")
    return value
