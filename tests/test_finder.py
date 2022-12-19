from tabulous import TableViewer
from tabulous import commands as cmds
import pandas as pd
from ._utils import selection_equal

def test_find_by_value():
    viewer = TableViewer(show=False)
    layer = viewer.add_table(
        pd.DataFrame({'a': [1, 2, 3], 'b': [2, 3, 2], 'c': ["a", "2", "2"]})
    )
    finder = cmds.table.show_finder_widget(viewer)
    finder.searchBox().setText("2")

    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findNext()
    selection_equal(layer.selections, [(0, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(2, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findPrevious()
    selection_equal(layer.selections, [(2, 1)])
    finder.findPrevious()
    selection_equal(layer.selections, [(0, 1)])

def test_find_by_text():
    viewer = TableViewer(show=False)
    layer = viewer.add_spreadsheet(
        pd.DataFrame({'a': ["aa", "bb", "cc"], 'b': ["bc", "cc", "cc"]})
    )
    finder = cmds.table.show_finder_widget(viewer)
    finder.searchBox().setText("cc")

    finder.findNext()
    selection_equal(layer.selections, [(2, 0)])
    finder.findNext()
    selection_equal(layer.selections, [(1, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(2, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(2, 0)])
    finder.findPrevious()
    selection_equal(layer.selections, [(2, 1)])
    finder.findPrevious()
    selection_equal(layer.selections, [(1, 1)])

def test_find_by_partial_text():
    viewer = TableViewer(show=False)
    layer = viewer.add_spreadsheet(
        pd.DataFrame({'a': ["aa", "bb", "cc"], 'b': ["bc", "cc", "cb"]})
    )
    finder = cmds.table.show_finder_widget(viewer)
    finder.searchBox().setText("b")
    finder.cbox_match.setCurrentIndex(2)  # partial match

    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findNext()
    selection_equal(layer.selections, [(0, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(2, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findPrevious()
    selection_equal(layer.selections, [(2, 1)])
    finder.findPrevious()
    selection_equal(layer.selections, [(0, 1)])


def test_find_by_regex():
    viewer = TableViewer(show=False)
    layer = viewer.add_spreadsheet(
        pd.DataFrame({'a': ["a123a", "b321b", "c2h2c"], 'b': ["a442a", "1cc2", "a12a"]})
    )
    finder = cmds.table.show_finder_widget(viewer)
    finder.searchBox().setText(r"a\d+a")
    finder.cbox_match.setCurrentIndex(3)  # regex

    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findNext()
    selection_equal(layer.selections, [(0, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(2, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findPrevious()
    selection_equal(layer.selections, [(2, 1)])
    finder.findPrevious()
    selection_equal(layer.selections, [(0, 1)])


def test_find_by_eval():
    viewer = TableViewer(show=False)
    layer = viewer.add_spreadsheet(
        pd.DataFrame({'a': ["0.13", "a", "2.5"], 'b': ["0.32", "-1.2", "0.54"]})
    )
    finder = cmds.table.show_finder_widget(viewer)
    finder.searchBox().setText("0 < float(x) < 1")
    finder.cbox_match.setCurrentIndex(4)  # eval

    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findNext()
    selection_equal(layer.selections, [(0, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(2, 1)])
    finder.findNext()
    selection_equal(layer.selections, [(1, 0)])
    finder.findPrevious()
    selection_equal(layer.selections, [(2, 1)])
    finder.findPrevious()
    selection_equal(layer.selections, [(0, 1)])
