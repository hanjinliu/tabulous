from typing import TYPE_CHECKING
import threading

if TYPE_CHECKING:
    from ._widget import QtConsole
    from tabulous.widgets._mainwindow import TableViewerBase

THREAD: "threading.Thread | None" = None


def _import_qtconsole() -> "type[QtConsole]":
    from ._widget import QtConsole

    return QtConsole


def import_qtconsole_threading() -> None:
    global THREAD

    if THREAD is None:
        THREAD = threading.Thread(target=_import_qtconsole, daemon=True)
        THREAD.start()
    else:
        THREAD.join()


def get_qtconsole(parent: "TableViewerBase") -> "QtConsole":
    import_qtconsole_threading()
    qtconsole = _import_qtconsole()()
    qtconsole.connect_parent(parent)
    return qtconsole
