from __future__ import annotations

from typing import NamedTuple, Protocol
import numpy as np
import pandas as pd

from magicgui import magicgui
from magicgui.widgets import (
    Container,
    Dialog,
    PushButton,
    RadioButton,
    ComboBox,
    Label,
    TextEdit,
)

from tabulous._magicgui import find_current_table, SelectionWidget
from ._models import MODELS, ADVANCED
from tabulous._qt._qt_const import MonospaceFontFamily


class SkLearnInput(NamedTuple):
    """Input for sklearn algorithms"""

    X: np.ndarray
    Y: np.ndarray | None
    labels: list[str]


class XYContainer(Container):
    """Data selection widgets for sklearn algorithms."""

    def __init__(self, **kwargs):
        self._X_widget = SelectionWidget(format="iloc", name="X")
        self._Y_widget = SelectionWidget(format="iloc", name="Y")
        super().__init__(widgets=[self._X_widget, self._Y_widget], **kwargs)
        self.margins = (0, 0, 0, 0)

    def get_values(self, df: pd.DataFrame) -> SkLearnInput:
        df_sub = self._X_widget.value.operate(df)
        X = df_sub.values
        labels = df_sub.columns.tolist()
        if self._Y_widget.value is not None:
            Y = self._Y_widget.value.operate(df)

            if Y.shape[1] != 1:
                raise ValueError("Label must be a single column")
            if Y.shape[0] != X.shape[0]:
                raise ValueError("Label and data must have the same number of rows")
            Y = Y.values.ravel()
            if Y.dtype.kind not in "ui":
                lut, Y = np.unique(Y, return_inverse=True)
        else:
            Y = None

        return SkLearnInput(X, Y, labels)


class SkLearnModelProtocol(Protocol):
    """A protocol for sklearn models"""

    # fmt: off
    def fit(self, X: np.ndarray, Y: np.ndarray | None = None): ...
    def predict(self, X: np.ndarray) -> np.ndarray: ...
    def fit_predict(self, X: np.ndarray, Y: np.ndarray | None = None) -> np.ndarray: ...
    def transform(self, X: np.ndarray) -> np.ndarray: ...
    def score(self, X: np.ndarray, Y: np.ndarray | None = None) -> float: ...
    def get_params(self, deep: bool = True) -> dict: ...
    # fmt: on


class SkLearnModelEdit(Container):
    """Widget for editing sklearn models and constructing them."""

    def __init__(self, **kwargs):
        self._text = Label(name="Model", value="")
        self._text.min_width = 200
        self._btn = PushButton(text="Select model")
        self._check = RadioButton(
            value=False, label="Advanced", tooltip="Check to show more models"
        )
        self._model: SkLearnModelProtocol | None = None

        super().__init__(
            widgets=[self._text, self._btn, self._check],
            labels=False,
            layout="horizontal",
            **kwargs,
        )
        # disconnect existing signales
        self._text.changed.disconnect()
        self._btn.changed.disconnect()
        self._check.changed.disconnect()
        self._btn.changed.connect(self._on_clicked)
        self._check.changed.connect(self._on_check_changed)

    @property
    def model(self) -> SkLearnModelProtocol | None:
        return self._model

    def _on_clicked(self):
        _model_choice = ComboBox(choices=MODELS.keys(), nullable=False)
        if model_name := self._text.value:
            model_name: str
            if model_name.endswith(" (fitted)"):
                model_name = model_name[:-9]
            _model_choice.value = model_name
        container = Container(widgets=[], labels=False)
        container.margins = (0, 0, 0, 0)

        dlg = Dialog(widgets=[_model_choice, container])

        @_model_choice.changed.connect
        def _on_model_changed():
            if model_name := _model_choice.value:
                model_factory = MODELS[model_name]
                gui = magicgui(model_factory, call_button=False)
                if len(container) > 0:
                    container.clear()
                container.append(gui)

        _model_choice.changed.emit(_model_choice.value)
        if dlg.exec():
            mgui = dlg[-1][0]
            self._model = mgui()
            self._text.value = _model_choice.value
            self.changed.emit(self._model)
        return None

    def _on_check_changed(self, checked: bool):
        if checked:
            MODELS.show_keys()  # advanced mode
        else:
            MODELS.hide_keys(ADVANCED)  # basic mode
        return None


class SkLearnContainer(Container):
    """
    The main container widget for scikit-learn analysis.

    This widget contains a data selection widget, a model selection widget, and
    buttons that perform the analysis.
    """

    _current_widget = None

    def __init__(self, **kwargs):
        self._model_widget = SkLearnModelEdit(label="model")
        self._data_widget = XYContainer(label="data")

        self._fit_button = PushButton(label="Fit", tooltip="Fit model by data")
        self._predict_button = PushButton(
            label="Predict", tooltip="Predict labels by data"
        )
        self._fit_predict_button = PushButton(
            label="Fit/Predict", tooltip="Fit model and predict labels by data"
        )
        self._transform_button = PushButton(label="Transform", tooltip="Transform data")
        self._describe_button = PushButton(
            label="Describe", tooltip="Describe the model"
        )
        self._score_button = PushButton(label="Score", tooltip="Score the model")

        _hlayout_1 = Container(
            layout="horizontal",
            widgets=[
                self._fit_button,
                self._predict_button,
                self._fit_predict_button,
            ],
        )
        _hlayout_1.margins = (0, 0, 0, 0)
        _hlayout_2 = Container(
            layout="horizontal",
            widgets=[
                self._transform_button,
                self._describe_button,
                self._score_button,
            ],
        )
        _hlayout_2.margins = (0, 0, 0, 0)

        self._output_area = TextEdit(label="Output")
        self._output_area.max_height = 100
        self._output_area.read_only = True
        self._output_area.native.setFontFamily(MonospaceFontFamily)

        super().__init__(
            widgets=[
                self._model_widget,
                self._data_widget,
                _hlayout_1,
                _hlayout_2,
                self._output_area,
            ],
            **kwargs,
        )
        self.margins = (0, 0, 0, 0)

        # connect signals
        self._model_widget.changed.connect(self._on_model_changed)
        self._fit_button.changed.connect(self._fit)
        self._predict_button.changed.connect(self._predict)
        self._fit_predict_button.changed.connect(self._fit_predict)
        self._transform_button.changed.connect(self._transform)
        self._describe_button.changed.connect(self._describe)
        self._score_button.changed.connect(self._score)

    @classmethod
    def new(cls) -> SkLearnContainer:
        """Build a new widget (singleton constructor)."""
        if cls._current_widget is None:
            cls._current_widget = SkLearnContainer()
        return cls._current_widget

    def _on_model_changed(self, model: SkLearnModelProtocol):
        """Check attributes of the model and enable/disable buttons."""
        self._predict_button.enabled = hasattr(model, "predict")
        self._fit_predict_button.enabled = hasattr(model, "fit_predict")
        self._transform_button.enabled = hasattr(model, "transform")
        self._score_button.enabled = hasattr(model, "score")

    def _fit(self):
        """Run self.fit(X, Y)."""
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        self._model_widget.model.fit(input.X, input.Y)
        text: str = self._model_widget._text.value
        if not text.endswith(" (fitted)"):
            self._model_widget._text.value = text + " (fitted)"

    def _predict(self):
        """Run self.predict(X)."""
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        predicted = self._model_widget.model.predict(input.X)
        name = table.columns.coerce_name("predicted")
        table.assign({name: predicted})
        table.selections = [(slice(None), table.columns.get_loc(name))]

        # update Y if it is empty
        if input.Y is None:
            self._data_widget._Y_widget._read_selection(table)
        return None

    def _fit_predict(self):
        """Run self.fit_predict(X, Y)."""
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        predicted = self._model_widget.model.fit_predict(input.X, input.Y)
        text: str = self._model_widget._text.value
        if not text.endswith(" (fitted)"):
            self._model_widget._text.value = text + " (fitted)"
        name = table.columns.coerce_name("predicted")
        table.assign({name: predicted})
        table.selections = [(slice(None), table.columns.get_loc(name))]

        # update Y if it is empty
        if input.Y is None:
            self._data_widget._Y_widget._read_selection(table)
        return None

    def _transform(self):
        """Run self.transform(X)."""
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        transformed = self._model_widget.model.transform(input.X)
        df_dict = {}
        for i in range(transformed.shape[1]):
            name = table.columns.coerce_name(f"transformed", start=i)
            df_dict[name] = transformed[:, i]
        nc_before = len(table.columns)
        table.assign(df_dict)
        nc_after = len(table.columns)
        table.selections = [(slice(None), slice(nc_before, nc_after))]
        return None

    def _describe(self):
        """Describe current model state."""
        model = self._model_widget.model
        output: list[str] = []
        params = model.get_params()
        output.append(f"parameters = \n{params}")

        for k, v in vars(model).items():
            if k.endswith("_"):
                output.append(f"{k} = \n{v}")

        self._output_area.value = "\n\n".join(output)
        return None

    def _score(self):
        """Run self.score(X)."""
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        score = self._model_widget.model.score(input.X, input.Y)
        self._output_area.value = f"score = {score}"
