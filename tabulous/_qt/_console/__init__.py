from typing import TYPE_CHECKING
from tabulous._async_importer import AsyncImporter

if TYPE_CHECKING:
    from ._widget import QtConsole
    from tabulous.widgets._mainwindow import TableViewerBase


@AsyncImporter
def _import_qtconsole() -> "type[QtConsole]":
    from ._widget import QtConsole

    return QtConsole


def import_qtconsole_threading() -> None:
    return _import_qtconsole.run()


def get_qtconsole(parent: "TableViewerBase") -> "QtConsole":
    qtconsole = _import_qtconsole.get()()
    qtconsole.connect_parent(parent)
    return qtconsole
