from __future__ import annotations

from typing import NamedTuple, Protocol
import numpy as np
import pandas as pd

from magicgui import magicgui
from magicgui.widgets import (
    Container,
    Dialog,
    PushButton,
    ComboBox,
    Label,
    Select,
    TextEdit,
)

from tabulous._magicgui import find_current_table, SelectionWidget
from ._models import MODELS


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
        else:
            Y = None

        return SkLearnInput(X, Y, labels)


class SkLearnModelProtocol(Protocol):
    """A protocol for sklearn models"""

    def fit(self, X: np.ndarray, Y: np.ndarray | None = None):
        ...

    def predict(self, X: np.ndarray) -> np.ndarray:
        ...

    def transform(self, X: np.ndarray) -> np.ndarray:
        ...

    def score(self, X: np.ndarray, Y: np.ndarray | None = None) -> float:
        ...

    def get_params(self, deep: bool = True) -> dict:
        ...


class SkLearnModelEdit(Container):
    """Widget for editing sklearn models and constructing them."""

    def __init__(self, **kwargs):
        self._text = Label(name="Model", value="")
        self._text.min_width = 200
        self._btn = PushButton(name="Select model")
        self._model: SkLearnModelProtocol | None = None

        super().__init__(
            widgets=[self._text, self._btn], labels=False, layout="horizontal", **kwargs
        )
        # disconnect existing signales
        self._text.changed.disconnect()
        self._btn.changed.disconnect()
        self._btn.changed.connect(self._on_clicked)

    @property
    def model(self) -> SkLearnModelProtocol | None:
        return self._model

    def _on_clicked(self):
        _model_choice = ComboBox(choices=MODELS.keys(), nullable=False)
        if model_name := self._text.value:
            _model_choice.value = str(model_name).rstrip(" (fitted)")
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


class SkLearnContainer(Container):
    """
    The main container widget for scikit-learn analysis.

    This widget contains a data selection widget, a model selection widget, and
    buttons that perform the analysis.
    """

    _current_widget = None

    def __init__(self, **kwargs):
        self._model_widget = SkLearnModelEdit(name="model")
        self._data_widget = XYContainer(name="data")

        self._fit_button = PushButton(name="Fit", tooltip="Fit model by data")
        self._predict_button = PushButton(
            name="Predict", tooltip="Predict labels by data"
        )
        self._transform_button = PushButton(name="Transform", tooltip="Transform data")
        self._describe_button = PushButton(
            name="Describe", tooltip="Describe the model"
        )
        self._score_button = PushButton(name="Score", tooltip="Score the model")
        self._plot_button = PushButton(name="Plot", tooltip="Plot the model")

        _hlayout_1 = Container(
            layout="horizontal",
            widgets=[
                self._fit_button,
                self._predict_button,
                self._transform_button,
            ],
        )
        _hlayout_1.margins = (0, 0, 0, 0)
        _hlayout_2 = Container(
            layout="horizontal",
            widgets=[
                self._describe_button,
                self._score_button,
                self._plot_button,
            ],
        )
        _hlayout_2.margins = (0, 0, 0, 0)

        self._output_area = TextEdit(label="Output")
        self._output_area.max_height = 100
        self._output_area.read_only = True

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

        self._model_widget.changed.connect(self._on_model_changed)
        self._fit_button.changed.connect(self._fit)
        self._predict_button.changed.connect(self._predict)
        self._transform_button.changed.connect(self._transform)
        self._describe_button.changed.connect(self._describe)
        self._score_button.changed.connect(self._score)
        self._plot_button.changed.connect(self._plot)

    @classmethod
    def new(cls) -> SkLearnContainer:
        """Build a new widget."""
        if cls._current_widget is None:
            cls._current_widget = SkLearnContainer()
        return cls._current_widget

    def _on_model_changed(self, model: SkLearnModelProtocol):
        """Check attributes of the model and enable/disable buttons."""
        self._predict_button.enabled = hasattr(model, "predict")
        self._transform_button.enabled = hasattr(model, "transform")

    def _fit(self):
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        self._model_widget.model.fit(input.X, input.Y)
        text = self._model_widget._text.value
        if not text.endswith(" (fitted)"):
            self._model_widget._text.value = text + " (fitted)"

    def _predict(self):
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

    def _transform(self):
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
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        score = self._model_widget.model.score(input.X, input.Y)
        self._output_area.value = f"score = {score}"

    def _plot(self):
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)

        # specify dimension
        if input.X.shape[1] > 2:
            select = Select(choices=range(input.X.shape[1]))
            dlg = Dialog(
                widgets=[Label(value="Select two dimensions to plot"), select],
                labels=False,
            )
            if dlg.exec():
                if len(select.value) != 2:
                    raise ValueError("Select two.")
                dim0, dim1 = select.value
            else:
                return
        else:
            dim0, dim1 = 0, 1

        if input.Y is not None:
            unique_labels = np.unique(input.Y)

            for label in unique_labels:
                spec = input.Y == label
                if input.X.shape[1] == 1:
                    table.plt.hist(input.X[spec, 0], label=label)
                else:
                    table.plt.scatter(
                        input.X[spec, dim0], input.X[spec, dim1], label=label
                    )
        else:
            if input.X.shape[1] == 1:
                table.plt.hist(input.X[:, 0], label=label)
            else:
                table.plt.scatter(input.X[:, dim0], input.X[:, dim1])

        if input.X.shape[1] == 1:
            table.plt.xlabel(input.labels[0])
        else:
            table.plt.xlabel(input.labels[dim0])
            table.plt.ylabel(input.labels[dim1])
