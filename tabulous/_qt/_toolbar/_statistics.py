from __future__ import annotations

from typing import List, NamedTuple
from enum import Enum
from scipy import stats
import numpy as np
import pandas as pd
from magicgui.widgets import Container, RadioButtons, ListEdit, PushButton

from tabulous._magicgui import find_current_table, SelectionWidget
from tabulous._selection_op import SelectionOperator
from tabulous.widgets import Table


class Test(Enum):
    t = "t-test"


def result_table(result: NamedTuple) -> Table:
    """Create a Table widget from a named tuple"""
    index = []
    data = []
    for k, v in result._asdict().items():
        index.append(k)
        data.append(v)
    df = pd.DataFrame(data, index=index, columns=["Results"])
    return Table(df)


class MeltedData(Container):
    def __init__(self, **kwargs):
        self._label_range_wdt = SelectionWidget(format="iloc", name="labels")
        self._data_range_wdt = SelectionWidget(format="iloc", name="data")
        super().__init__(
            widgets=[self._label_range_wdt, self._data_range_wdt], **kwargs
        )

    def extract_dataset(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        label = self._label_range_wdt.value.operate(df)
        data = self._data_range_wdt.value.operate(df)

        if label.shape[1] != 1:
            raise ValueError("Label must be a single column")
        if data.shape[1] != 1:
            raise ValueError("Data must be a single column")

        label = np.asarray(label.dropna()).ravel()
        data = np.asarray(data.dropna()).ravel()
        unique_labels = np.unique(label)
        return {l: data[label == l] for l in unique_labels}

    def all_selections(self, df: pd.DataFrame) -> list[tuple[slice, slice]]:
        range0 = self._label_range_wdt.value.as_iloc_slices(df)
        range1 = self._data_range_wdt.value.as_iloc_slices(df)
        return [range0, range1]


class UnstructuredData(Container):
    def __init__(self, **kwargs):
        self._data_range_list = ListEdit(
            annotation=List[SelectionOperator],
            name="data",
            layout="vertical",
            options=dict(format="iloc"),
        )
        super().__init__(widgets=[self._data_range_list], **kwargs)

    def extract_dataset(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        data_dict = {}
        for op in self._data_range_list.value:
            op: SelectionOperator
            data = op.operate(df)
            if len(data) == 2 and data.shape[1] != 1:
                raise ValueError("Data must be a single column")
            data_dict[data.columns[0]] = np.asarray(data.dropna()).ravel()
        return data_dict

    def all_selections(self, df: pd.DataFrame) -> list[tuple[slice, slice]]:
        return [op.as_iloc_slices(df) for op in self._data_range_list.value]


class StatsTestDialog(Container):
    def __init__(self, **kwargs):
        self._radio_buttons = RadioButtons(
            choices=["Separate data", "Labeled data"], value="Separate data"
        )
        self._separate_data = UnstructuredData()
        self._labeled_data = MeltedData()
        self._call_button = PushButton(text="Run")
        super().__init__(
            widgets=[
                self._radio_buttons,
                self._separate_data,
                self._labeled_data,
                self._call_button,
            ],
            **kwargs,
        )

        self._call_button.changed.connect(self._on_call)
        self._radio_buttons.changed.connect(self._on_radiobutton_changed)

    def _on_call(self):
        table = find_current_table(self)
        if table is None:
            raise ValueError("No table found")
        df = table.data
        if self._radio_buttons.value == "Separate data":
            widget = self._separate_data
        else:
            widget = self._labeled_data

        data_dict = widget.extract_dataset(df)
        self.close()
        if len(data_dict) == 2:
            results = stats.ttest_ind(*data_dict.values())
            table.add_side_widget(result_table(results))
            sels = widget.all_selections(df)
            # table.events.data.mloc(sels).connect()
        else:
            raise NotImplementedError

    def _on_radiobutton_changed(self, v):
        self._separate_data.visible = v == "Separate data"
        self._labeled_data.visible = v == "Labeled data"
