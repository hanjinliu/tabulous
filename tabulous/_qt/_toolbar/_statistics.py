from __future__ import annotations

from typing import List, NamedTuple, Sequence
from scipy import stats
import numpy as np
import pandas as pd
from magicgui.widgets import (
    Container,
    RadioButtons,
    ListEdit,
    PushButton,
    ComboBox,
    CheckBox,
)

from tabulous._magicgui import find_current_table, SelectionWidget
from tabulous._selection_op import SelectionOperator
from tabulous.widgets import Table


def result_table(result: NamedTuple) -> Table:
    """Create a Table widget from a named tuple"""
    index = []
    data = []
    for k, v in result._asdict().items():
        index.append(k)
        data.append(v)
    df = pd.DataFrame(data, index=index, columns=["Results"])
    return Table(df)


# ########################################################
#   Data container
# ########################################################


class DataContainer(Container):
    def extract_dataset(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        raise NotImplementedError

    def all_selections(self, df: pd.DataFrame) -> list[tuple[slice, slice]]:
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

        label = np.asarray(label).ravel()
        data = np.asarray(data).ravel()
        unique_labels = np.unique(label)
        return {l: data[label == l] for l in unique_labels}

    def all_selections(self, df: pd.DataFrame) -> list[tuple[slice, slice]]:
        range0 = self._label_range_wdt.value.as_iloc_slices(df)
        range1 = self._data_range_wdt.value.as_iloc_slices(df)
        return [range0, range1]


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

    def all_selections(self, df: pd.DataFrame) -> list[tuple[slice, slice]]:
        return [op.as_iloc_slices(df) for op in self._data_range_list.value]


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
        self._alternative = ComboBox(
            choices=["two-sided", "greater", "less"],
            value="two-sided",
            name="alternative",
        )
        self._nan_policy = ComboBox(
            choices=["propagate", "omit", "raise"], value="omit", name="nan_values"
        )
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
            raise RuntimeError("Unreachable")


class MannwhitneyuRunner(TestRunner):
    """Parameters for Mann-Whitney U-test"""

    def __init__(self, **kwargs):
        self._alternative = ComboBox(
            choices=["two-sided", "greater", "less"],
            value="two-sided",
            name="alternative",
        )
        self._nan_policy = ComboBox(
            choices=["propagate", "omit", "raise"], value="omit", name="nan_values"
        )
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
        self._nan_policy = ComboBox(
            choices=["propagate", "omit", "raise"], value="omit", name="nan_values"
        )
        super().__init__(widgets=[self._nan_policy], **kwargs)
        self.margins = (0, 0, 0, 0)

    def run_test(self, data: Sequence[np.ndarray]):
        return stats.kruskal(*data, nan_policy=self._nan_policy.value)


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
            choices=[TestTypes.T, TestTypes.U, TestTypes.H],
            value=TestTypes.T,
        )
        self._test_runners: dict[str, TestRunner] = {
            TestTypes.T: TtestRunner(),
            TestTypes.U: MannwhitneyuRunner(),
            TestTypes.H: KruskalRunner(),
        }

        self._call_button = PushButton(text="Run")

        super().__init__(
            widgets=[
                self._data_types,
                *self._data_containers.values(),
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
        table.add_side_widget(result_table(results))
        sels = widget.all_selections(df)
        # table.events.data.mloc(sels).connect()

    def _on_data_type_changed(self, v):
        for k, w in self._data_containers.items():
            w.visible = k == v

    def _on_test_type_changed(self, v):
        for k, w in self._test_runners.items():
            w.visible = k == v
