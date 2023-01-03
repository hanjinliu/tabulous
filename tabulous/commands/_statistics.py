from __future__ import annotations

from typing import List, NamedTuple, Sequence
from functools import partial
from scipy import stats
import numpy as np
import pandas as pd
from magicgui.widgets import (
    Container,
    RadioButtons,
    ListEdit,
    PushButton,
    ComboBox,
    Label,
)

from tabulous._magicgui import find_current_table, SelectionWidget
from tabulous._selection_op import SelectionOperator
from tabulous.exceptions import UnreachableError
from tabulous.widgets import Table


def result_table(result: NamedTuple) -> Table:
    """Create a Table widget from a named tuple"""
    index = []
    data = []
    for k, v in result._asdict().items():
        index.append(k)
        data.append(v)
    df = pd.DataFrame(data, index=index, columns=[type(result).__name__])
    return Table(df, editable=False)


combobox_alternative = partial(
    ComboBox,
    choices=["two-sided", "greater", "less"],
    value="two-sided",
    name="alternative",
    tooltip="Alternative hypothesis",
)

combobox_nan_policy = partial(
    ComboBox,
    choices=["propagate", "omit", "raise"],
    value="omit",
    name="nan_values",
    tooltip="How to handle NaN values",
)

# ########################################################
#   Data container
# ########################################################


class DataContainer(Container):
    def extract_dataset(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        raise NotImplementedError


class MeltedDataContainer(DataContainer):
    """Data container for melted data, a column for labels and one for data."""

    def __init__(self, **kwargs):
        self._label_range_wdt = SelectionWidget(format="iloc", name="labels")
        self._data_range_wdt = SelectionWidget(format="iloc", name="data")
        super().__init__(
            widgets=[self._label_range_wdt, self._data_range_wdt], **kwargs
        )
        self.margins = (0, 0, 0, 0)

    def extract_dataset(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        label = self._label_range_wdt.value.operate(df)
        data = self._data_range_wdt.value.operate(df)

        if label.shape[1] != 1:
            raise ValueError("Label must be a single column")
        if data.shape[1] != 1:
            raise ValueError("Data must be a single column")
        if label.size != data.size:
            raise ValueError("Label and data must have the same size")

        label = np.asarray(label).ravel()
        data = np.asarray(data).ravel()
        unique_labels = np.unique(label)
        return {_l: data[label == _l] for _l in unique_labels}


class UnstructuredDataContainer(DataContainer):
    """Data container for unstructured data, each column for each data."""

    def __init__(self, **kwargs):
        self._data_range_list = ListEdit(
            value=[None, None],
            annotation=List[SelectionOperator],
            name="data",
            layout="vertical",
            options=dict(format="iloc"),
        )
        super().__init__(widgets=[self._data_range_list], **kwargs)
        self.margins = (0, 0, 0, 0)

    def extract_dataset(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        data_dict = {}
        for op in self._data_range_list.value:
            op: SelectionOperator
            data = op.operate(df)
            if data.shape[1] != 1:
                raise ValueError("Data must be a single column")
            data_dict[data.columns[0]] = np.asarray(data).ravel()
        return data_dict


# ########################################################
#   Parameters for each test
# ########################################################


class TestRunner(Container):
    def run_test(self, data: Sequence[np.ndarray]) -> NamedTuple:
        raise NotImplementedError


class TtestRunner(TestRunner):
    """Parameters for t-test"""

    def __init__(self, **kwargs):
        self._test_type = ComboBox(
            choices=["Student's", "Welch's", "Related"], name="type"
        )
        self._alternative = combobox_alternative()
        self._nan_policy = combobox_nan_policy()
        super().__init__(
            widgets=[self._test_type, self._alternative, self._nan_policy],
            **kwargs,
        )
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        if len(data) != 2:
            raise ValueError("t-test only supports two data sets")
        kwargs = dict(
            alternative=self._alternative.value,
            nan_policy=self._nan_policy.value,
        )
        if self._test_type.value == "Student's":
            return stats.ttest_ind(data[0], data[1], **kwargs)
        elif self._test_type.value == "Welch's":
            return stats.ttest_ind(data[0], data[1], equal_var=False, **kwargs)
        elif self._test_type.value == "Related":
            return stats.ttest_rel(data[0], data[1], **kwargs)
        else:
            raise UnreachableError(self._test_type)


class MannwhitneyuRunner(TestRunner):
    """Parameters for Mann-Whitney U-test"""

    def __init__(self, **kwargs):
        self._alternative = combobox_alternative()
        self._nan_policy = combobox_nan_policy()
        super().__init__(widgets=[self._alternative, self._nan_policy], **kwargs)
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        if len(data) != 2:
            raise ValueError("Mann-Whitney U-test only supports two data sets")
        return stats.mannwhitneyu(
            data[0],
            data[1],
            alternative=self._alternative.value,
            nan_policy=self._nan_policy.value,
        )


class KruskalRunner(TestRunner):
    """Parameters for Kruskal-Wallis H test"""

    def __init__(self, **kwargs):
        self._nan_policy = combobox_nan_policy()
        super().__init__(widgets=[self._nan_policy], **kwargs)
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        return stats.kruskal(*data, nan_policy=self._nan_policy.value)


class WilcoxonRunner(TestRunner):
    """Parameters for Wilcoxon signed-rank test"""

    def __init__(self, **kwargs):
        self._alternative = combobox_alternative()
        self._nan_policy = combobox_nan_policy()
        super().__init__(widgets=[self._alternative, self._nan_policy], **kwargs)
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        if len(data) != 2:
            raise ValueError("Wilcoxon signed-rank test only supports two data sets")
        return stats.wilcoxon(
            data[0],
            data[1],
            alternative=self._alternative.value,
            nan_policy=self._nan_policy.value,
        )


class FriedmanRunner(TestRunner):
    """Parameters for Friedman test"""

    def __init__(self, **kwargs):
        super().__init__(widgets=[], **kwargs)
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        return stats.friedmanchisquare(*data)


class AnovaRunner(TestRunner):
    """Parameters for ANOVA"""

    def __init__(self, **kwargs):
        super().__init__(widgets=[], **kwargs)
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        return stats.f_oneway(*data)


# ########################################################
#   Main widget
# ########################################################


class DataTypes:
    """Choices for data types"""

    SEPARATE = "Separate data"
    LABELED = "Labeled data"


class TestTypes:
    """Choices for test types"""

    T = "Student's t-test"
    U = "Mann-Whitney U-test"
    H = "Kruskal-Wallis H-test"
    Wilcoxon = "Wilcoxon signed-rank test"
    Friedman = "Friedman test"
    ANOVA = "one-way ANOVA"

    _all = [T, U, H, Wilcoxon, Friedman, ANOVA]


class StatsTestDialog(Container):
    def __init__(self, **kwargs):
        self._data_types = RadioButtons(
            choices=[DataTypes.SEPARATE, DataTypes.LABELED], value=DataTypes.SEPARATE
        )
        self._data_containers: dict[str, DataContainer] = {
            DataTypes.SEPARATE: UnstructuredDataContainer(),
            DataTypes.LABELED: MeltedDataContainer(),
        }

        self._test_types = ComboBox(
            choices=TestTypes._all,
            value=TestTypes.T,
        )
        self._test_runners: dict[str, TestRunner] = {
            TestTypes.T: TtestRunner(),
            TestTypes.U: MannwhitneyuRunner(),
            TestTypes.H: KruskalRunner(),
            TestTypes.Wilcoxon: WilcoxonRunner(),
            TestTypes.Friedman: FriedmanRunner(),
            TestTypes.ANOVA: AnovaRunner(),
        }

        self._call_button = PushButton(text="Run")

        super().__init__(
            widgets=[
                Label(value="Input datasets"),
                self._data_types,
                *self._data_containers.values(),
                Label(value="Test method and parameters"),
                self._test_types,
                *self._test_runners.values(),
                self._call_button,
            ],
            **kwargs,
        )

        self._call_button.changed.connect(self._on_call)
        self._data_types.changed.connect(self._on_data_type_changed)
        self._test_types.changed.connect(self._on_test_type_changed)
        self._on_data_type_changed(DataTypes.SEPARATE)
        self._on_test_type_changed(TestTypes.T)

    def _on_call(self):
        table = find_current_table(self)
        if table is None:
            raise ValueError("No table found")
        df = table.data
        widget = self._data_containers[self._data_types.value]

        data_dict = widget.extract_dataset(df)
        self.close()

        data_input = list(data_dict.values())
        results = self._test_runners[self._test_types.value].run_test(data_input)
        table.add_side_widget(result_table(results), name="Test result")

    def _on_data_type_changed(self, v):
        for k, w in self._data_containers.items():
            w.visible = k == v

    def _on_test_type_changed(self, v):
        for k, w in self._test_runners.items():
            w.visible = k == v
