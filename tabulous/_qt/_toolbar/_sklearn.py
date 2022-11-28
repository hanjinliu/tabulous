from __future__ import annotations

from typing import NamedTuple, Protocol
from typing_extensions import Annotated, Literal
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

from sklearn.cluster import (
    KMeans,
    DBSCAN,
    AgglomerativeClustering,
    OPTICS,
    SpectralClustering,
    AffinityPropagation,
    Birch,
    MeanShift,
)
from sklearn.mixture import GaussianMixture


class SkLearnInput(NamedTuple):
    """Input for sklearn algorithms"""

    X: np.ndarray
    Y: np.ndarray | None
    labels: list[str]


class XYContainer(Container):
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


def _normalize_random_state(state) -> int | None:
    if state:
        return int(state)
    else:
        return None


# Model factories
def kmeans(
    n_clusters: int = 8,
    init: Literal["k-means++", "random"] = "k-means++",
    n_init: Annotated[int, {"min": 1, "max": 100}] = 10,
    max_iter: Annotated[int, {"min": 1, "max": 10000}] = 300,
    tol: str = "1e-4",
    random_state: str = "",
):
    random_state = _normalize_random_state(random_state)
    tol = float(tol)
    return KMeans(
        n_clusters=n_clusters,
        init=init,
        n_init=n_init,
        max_iter=max_iter,
        tol=tol,
        random_state=random_state,
    )


def dbscan(
    eps: Annotated[float, {"min": 0.0, "max": 1000.0}] = 0.5,
    min_samples: Annotated[int, {"min": 1, "max": 100}] = 5,
    metric: str = "euclidean",
    algorithm: Literal["auto", "ball_tree", "kd_tree", "brute"] = "auto",
    leaf_size: Annotated[int, {"min": 1, "max": 100}] = 30,
    p: Annotated[int, {"min": 1, "max": 100}] = 2,
    n_jobs: Annotated[int, {"min": 1, "max": 100}] = None,
):
    return DBSCAN(
        eps=eps,
        min_samples=min_samples,
        metric=metric,
        algorithm=algorithm,
        leaf_size=leaf_size,
        p=p,
        n_jobs=n_jobs,
    )


def agglomerative(
    n_clusters: Annotated[int, {"min": 1, "max": 100}] = 2,
    affinity: Literal[
        "euclidean", "l1", "l2", "manhattan", "cosine", "precomputed"
    ] = "euclidean",
    compute_full_tree: Literal["auto", "true", "false"] = "auto",
    linkage: Literal["ward", "complete", "average", "single"] = "ward",
):
    return AgglomerativeClustering(
        n_clusters=n_clusters,
        affinity=affinity,
        compute_full_tree=compute_full_tree,
        linkage=linkage,
    )


def optics(
    min_samples: Annotated[int, {"min": 1, "max": 100}] = 5,
    max_eps: Annotated[float, {"min": 0.0, "max": 100.0}] = np.inf,
    metric: str = "minkowski",
    algorithm: Literal["auto", "ball_tree", "kd_tree", "brute"] = "auto",
    leaf_size: Annotated[int, {"min": 1, "max": 100}] = 30,
    p: Annotated[int, {"min": 1, "max": 100}] = 2,
    n_jobs: Annotated[int, {"min": 1, "max": 100}] = None,
):
    return OPTICS(
        min_samples=min_samples,
        max_eps=max_eps,
        metric=metric,
        algorithm=algorithm,
        leaf_size=leaf_size,
        p=p,
        n_jobs=n_jobs,
    )


def spectral(
    n_clusters: Annotated[int, {"min": 1, "max": 100}] = 8,
    eigen_solver: Literal["arpack", "lobpcg", "amg"] = "arpack",
    random_state: str = "",
    n_init: Annotated[int, {"min": 1, "max": 100}] = 10,
    gamma: Annotated[float, {"min": 0.0, "max": 100.0}] = 1.0,
    affinity: Literal["nearest_neighbors", "rbf"] = "rbf",
    n_neighbors: Annotated[int, {"min": 1, "max": 100}] = 10,
    eigen_tol: Annotated[float, {"min": 0.0, "max": 100.0}] = 0.0,
    assign_labels: Literal["kmeans", "discretize"] = "kmeans",
    degree: float = 3,
    coef0: float = 1,
):
    random_state = _normalize_random_state(random_state)
    return SpectralClustering(
        n_clusters=n_clusters,
        eigen_solver=eigen_solver,
        random_state=random_state,
        n_init=n_init,
        gamma=gamma,
        affinity=affinity,
        n_neighbors=n_neighbors,
        eigen_tol=eigen_tol,
        assign_labels=assign_labels,
        degree=degree,
        coef0=coef0,
    )


def gaussian_mixture(
    n_components: Annotated[int, {"min": 1, "max": 100}] = 1,
    covariance_type: Literal["full", "tied", "diag", "spherical"] = "full",
    tol: str = "1e-3",
    reg_covar: Annotated[float, {"min": 0.0, "max": 100.0}] = 1e-6,
    max_iter: Annotated[int, {"min": 1, "max": 1000}] = 100,
    n_init: Annotated[int, {"min": 1, "max": 100}] = 1,
    init_params: Literal["kmeans", "random"] = "kmeans",
    random_state: str = "",
):
    random_state = _normalize_random_state(random_state)
    tol = float(tol)
    return GaussianMixture(
        n_components=n_components,
        covariance_type=covariance_type,
        tol=tol,
        reg_covar=reg_covar,
        max_iter=max_iter,
        n_init=n_init,
        init_params=init_params,
        random_state=random_state,
    )


MODELS = {
    "KMeans": kmeans,
    "DBSCAN": dbscan,
    "AgglomerativeClustering": agglomerative,
    "OPTICS": optics,
    "SpectralClustering": spectral,
    "AffinityPropagation": AffinityPropagation,
    "Birch": Birch,
    "MeanShift": MeanShift,
    "GaussianMixture": gaussian_mixture,
}


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
    def __init__(self, **kwargs):
        self._text = Label(name="Model", value="")
        self._text.min_width = 200
        self._btn = PushButton(name="Select model")
        self._model = None

        super().__init__(
            widgets=[self._text, self._btn], labels=False, layout="horizontal", **kwargs
        )

        self._btn.changed.connect(self._on_clicked)

    @property
    def model(self) -> SkLearnModelProtocol | None:
        return self._model

    def _on_clicked(self):
        _model_choice = ComboBox(choices=MODELS.keys(), nullable=False)
        if model_name := self._text.value:
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


class SkLearnContainer(Container):
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

    def _fit(self):
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        self._model_widget.model.fit(input.X, input.Y)
        self._model_widget._text.value = self._model_widget._text.value + " (fitted)"

    def _predict(self):
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        predicted = self._model_widget.model.predict(input.X)
        table.cell[: predicted.shape[0], None] = predicted

        # update Y if it is empty
        if input.Y is None:
            self._data_widget._Y_widget._read_selection(table)

    def _transform(self):
        table = find_current_table(self)
        input = self._data_widget.get_values(table.data)
        transformed = self._model_widget.model.transform(input.X)
        table.cell[: transformed.shape[0], None] = transformed

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
