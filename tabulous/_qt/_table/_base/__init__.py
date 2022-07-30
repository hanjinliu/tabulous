from ._model_base import AbstractDataFrameModel, DataFrameModel
from ._table_base import (
    QBaseTable,
    QMutableTable,
    QMutableSimpleTable,
    _QTableViewEnhanced,
)

__all__ = [
    "AbstractDataFrameModel",
    "DataFrameModel",
    "QBaseTable",
    "QMutableTable",
    "QMutableSimpleTable",
    "_QTableViewEnhanced",
]

# #############################################################################
#   install keycombo
# #############################################################################

QBaseTable._keymap.bind("Ctrl+C", QBaseTable.copyToClipboard, headers=False)
QBaseTable._keymap.bind("Ctrl+C, Ctrl+H", QBaseTable.copyToClipboard, headers=True)


@QBaseTable._keymap.bind("Ctrl+Up", row=0, column=None)
@QBaseTable._keymap.bind("Ctrl+Down", row=-1, column=None)
@QBaseTable._keymap.bind("Ctrl+Left", row=None, column=0)
@QBaseTable._keymap.bind("Ctrl+Right", row=None, column=-1)
def _(self: QBaseTable, row, column):
    self.moveToItem(row, column)


@QMutableTable._keymap.bind("Ctrl+X")
def _(self: QMutableTable):
    self.copyToClipboard(headers=False)
    return self.deleteValues()


QMutableTable._keymap.bind("Ctrl+V", QMutableTable.pasteFromClipBoard)
QMutableTable._keymap.bind("Delete", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Backspace", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Ctrl+Z", QMutableTable.undo)
QMutableTable._keymap.bind("Ctrl+Y", QMutableTable.redo)
