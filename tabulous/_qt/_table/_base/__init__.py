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
QBaseTable._keymap.bind("Ctrl+Shift+C", QBaseTable.copyToClipboard, headers=True)

QMutableTable._keymap.bind("Ctrl+V", QMutableTable.pasteFromClipBoard)
QMutableTable._keymap.bind("Delete", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Backspace", QMutableTable.deleteValues)
QMutableTable._keymap.bind("Ctrl+Z", QMutableTable.undo)
QMutableTable._keymap.bind("Ctrl+Y", QMutableTable.redo)
QMutableTable._keymap.bind(["Ctrl+K", "E"], QMutableTable.toggleEditability)
