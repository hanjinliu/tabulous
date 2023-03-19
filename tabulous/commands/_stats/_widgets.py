from typing import Iterable

from qtpy import QtWidgets as QtW, QtGui
from superqt import QEnumComboBox


from ._distribution import Distributions
from ._latex import QLatexLabel


class QScipyStatsWidget(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout()
        self._dist = QEnumComboBox(enum_class=Distributions)
        self._dist.setCurrentEnum(Distributions.norm)
        self._latex_label = QLatexLabel(Distributions.norm.latex)
        if parent is not None:
            self._latex_label.setTextColor(
                parent.palette().color(QtGui.QPalette.ColorRole.Text)
            )
        self._params = QStatsParameterWidget(Distributions.norm.params)
        _layout.addWidget(self._dist)
        _layout.addWidget(self._latex_label)
        _layout.addWidget(self._params)

        self.setLayout(_layout)
        self._dist.currentEnumChanged.connect(self._dist_changed)

    def _dist_changed(self, dist: Distributions):
        self._latex_label.setLatex(dist.latex)
        self._params.set_labels(dist.params)
        self.adjustSize()


class QStatsParameterWidget(QtW.QWidget):
    def __init__(
        self, labels: Iterable[str], parent: QtW.QWidget | None = None
    ) -> None:
        super().__init__(parent)
        _layout = QtW.QFormLayout()
        self._widgets: list[QtW.QLineEdit] = []
        self.setLayout(_layout)
        self.set_labels(labels)

    def get_params(self) -> list[float]:
        return [float(wdt.text()) for wdt in self._widgets]

    def set_params(self, param: Iterable[float]) -> None:
        for wdt, p in zip(self._widgets, param):
            wdt.setText(str(p))

    def set_labels(self, labels: Iterable[str]) -> None:
        layout: QtW.QFormLayout = self.layout()
        while layout.rowCount() > 0:
            layout.removeRow(0)
        self._widgets: list[QtW.QLineEdit] = []
        for label in labels:
            wdt = QtW.QLineEdit()
            self._widgets.append(wdt)
            layout.addRow(label, wdt)


# @magic_factory
# def fit(
#     table: TableBase,
#     sel: SelectionOperator,
#     distribution: Distributions = Distributions.norm,
#     floc: str = "",
#     fscale: str = "",
# ):
#     import pandas as pd

#     df = sel.operate(table.data)
#     out: dict[str, tuple] = {}
#     dist = distribution.dist

#     kwargs = {}
#     if floc:
#         kwargs["floc"] = float(floc)
#     if fscale:
#         kwargs["fscale"] = float(fscale)

#     for col in df.columns:
#         d = dist.fit(df[col].values, **kwargs)
#         out[col] = d

#     df = pd.DataFrame(out, index=distribution.params)
#     table.add_side_widget(
#         Table(df, editable=False), name="Distribution Fitting Results"
#     )
