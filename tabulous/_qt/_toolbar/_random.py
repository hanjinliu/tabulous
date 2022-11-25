from __future__ import annotations

from enum import Enum
import numpy as np
from magicgui.widgets import (
    LineEdit,
    RadioButtons,
    Container,
    LiteralEvalLineEdit,
    PushButton,
    Widget,
)
from tabulous._magicgui import SelectionWidget


class _RandomGenerator(Container):
    def __init__(self, **kwargs):
        widgets = self.prepare_widgets()
        super().__init__(widgets=widgets, **kwargs)

    def prepare_widgets(self) -> list[Widget]:
        return []

    def generate(self, shape: tuple[int, int]) -> np.ndarray:
        raise NotImplementedError


class UniformRandomGenerator(_RandomGenerator):
    def prepare_widgets(self) -> list[Widget]:
        return [
            LineEdit(label="minimum"),
            LineEdit(label="maximum"),
        ]

    def generate(self, shape: tuple[int, int]) -> np.ndarray:
        val = np.random.random(shape)
        mn = float(self[0].value)
        mx = float(self[1].value)
        return mn + (mx - mn) * val


class ChoiceRandomGenerator(_RandomGenerator):
    def prepare_widgets(self) -> list[Widget]:
        return [
            LiteralEvalLineEdit(
                label="choices",
                tooltip="Iterable object that provide choices (e.g. [1, 3, 5])",
            ),
        ]

    def generate(self, shape: tuple[int, int]) -> np.ndarray:
        choices = self[0].value
        return np.random.choice(choices, shape)


class NormalRandomGenerator(_RandomGenerator):
    def prepare_widgets(self) -> list[Widget]:
        return [
            LineEdit(label="mean"),
            LineEdit(label="sigma"),
        ]

    def generate(self, shape: tuple[int, int]) -> np.ndarray:
        return np.random.normal(
            float(self[0].value),
            float(self[1].value),
            size=shape,
        )


class Generator(Enum):
    uniform = "uniform"
    normal = "normal"
    choices = "choices"


class RandomGeneratorDialog(Container):
    def __init__(self):
        self._selection_wdt = SelectionWidget(format="iloc")
        self._radio_buttons = RadioButtons(choices=Generator, value=Generator.uniform)
        self._uniform_wdt = UniformRandomGenerator(label="parameters")
        self._normal_wdt = NormalRandomGenerator(label="parameters")
        self._choices_wdt = ChoiceRandomGenerator(label="parameters")
        self._call_button = PushButton(text="Generate data")

        super().__init__(
            widgets=[
                self._selection_wdt,
                self._radio_buttons,
                self._uniform_wdt,
                self._normal_wdt,
                self._choices_wdt,
                self._call_button,
            ]
        )

        self._radio_buttons.changed.connect(self._on_choice_changed)
        self._radio_buttons.changed.emit(Generator.uniform)
        self.called = self._call_button.changed
        self.called.connect(self.close)

    def _on_choice_changed(self, choice: Generator):
        self._uniform_wdt.visible = choice == Generator.uniform
        self._normal_wdt.visible = choice == Generator.normal
        self._choices_wdt.visible = choice == Generator.choices

    def _current_widget(self) -> _RandomGenerator:
        for wdt in (self._uniform_wdt, self._normal_wdt, self._choices_wdt):
            if wdt.visible:
                return wdt
        else:
            raise RuntimeError("Unreachable error happened.")

    def get_value(self, df) -> tuple[slice, slice, np.ndarray]:
        selop = self._selection_wdt.value
        shape = selop.shape(df)
        random_data = self._current_widget().generate(shape)
        rslice, cslice = selop.as_iloc_slices(df)
        return rslice, cslice, random_data