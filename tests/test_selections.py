from tabulous import TableViewer, commands as cmds
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from ._utils import selection_equal, slice_equal

df0 = pd.DataFrame({"a": [10, 20, 30], "b": [1.0, 1.1, 1.2]})


def test_selection():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    table.selections = [(0, 0), (slice(1, 3), slice(1, 2))]

    sl0 = (slice(0, 1), slice(0, 1))
    sl1 = (slice(1, 3), slice(1, 2))
    assert selection_equal(table.selections, [sl0, (slice(1, 3), slice(1, 2))])
    assert slice_equal(table.selections[0], sl0)
    assert slice_equal(table.selections[1], sl1)
    assert_frame_equal(table.selections.values[0], table.data.iloc[sl0])
    assert_frame_equal(table.selections.values[1], table.data.iloc[sl1])

def test_highlight():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    table.highlights = [(0, 0), (slice(1, 3), slice(1, 2))]

    sl0 = (slice(0, 1), slice(0, 1))
    sl1 = (slice(1, 3), slice(1, 2))
    assert selection_equal(table.highlights, [sl0, (slice(1, 3), slice(1, 2))])
    assert slice_equal(table.highlights[0], sl0)
    assert slice_equal(table.highlights[1], sl1)
    assert_frame_equal(table.highlights.values[0], table.data.iloc[sl0])
    assert_frame_equal(table.highlights.values[1], table.data.iloc[sl1])

def test_selection_signal():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    mock = MagicMock()

    @table.events.selections.connect
    def f(sel):
        mock(sel)

    mock.assert_not_called()
    sel = [(slice(1, 2), slice(1, 2))]
    table.selections = sel
    mock.assert_called_once()
    mock.reset_mock()
    table._qwidget._qtable_view._selection_model.move_to(0, 0)
    mock.assert_called_once()


def test_selection_signal_recursive():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    mock = MagicMock()

    @table.events.selections.connect
    def f(sel):
        try:
            table.selections = [(0, 0)]
        except RuntimeError:
            mock()

    mock.assert_not_called()
    table.selections = [(1, 1)]
    mock.assert_called_once()

def test_list_like_methods():
    viewer = TableViewer(show=False)
    table = viewer.add_table(df0)
    table.selections.clear()
    table.selections.append((0, 0))
    assert selection_equal(table.selections, [(slice(0, 1), slice(0, 1))])
    table.selections.append((slice(1, 3), slice(1, 2)))
    assert selection_equal(table.selections, [(slice(0, 1), slice(0, 1)), (slice(1, 3), slice(1, 2))])
    table.selections.pop(0)
    assert selection_equal(table.selections, [(slice(1, 3), slice(1, 2))])
    table.selections.clear()
    assert selection_equal(table.selections, [])

def test_highlight_translation():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(np.zeros((10, 10)))
    sheet.highlights.append((slice(2, 5), slice(2, 5)))
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(2, 5))])
    sheet.columns.remove(0, 1)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(1, 4))])
    sheet.columns.insert(0, 2)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(3, 6))])
    sheet.columns.insert(6, 1)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(3, 6))])
    sheet.columns.remove(2, 1)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(2, 5))])
    sheet.columns.remove(2, 1)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(2, 4))])
    sheet.columns.remove(4, 1)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(2, 4))])
    sheet.columns.remove(3, 1)
    assert selection_equal(sheet.highlights, [(slice(2, 5), slice(2, 3))])
    sheet.columns.remove(2, 1)
    assert selection_equal(sheet.highlights, [])

def test_highlight_with_proxy():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(np.zeros((5, 5)))
    sheet.proxy.set([1, 3, 2, 4, 0])  # index is in this order
    sheet.selections = [((slice(1, 2), slice(0, 5)))]
    cmds.selection.add_highlight(viewer)
    assert selection_equal(sheet.highlights, [(slice(3, 4), slice(0, 5))])
    sheet.selections = [((slice(1, 3), slice(0, 5)))]
    with pytest.raises(Exception):
        cmds.selection.add_highlight(viewer)
