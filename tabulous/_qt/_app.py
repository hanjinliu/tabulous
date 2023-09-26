from __future__ import annotations

import sys
from qtpy.QtWidgets import QApplication
from qtpy.QtCore import Qt
from qtpy import PYQT5, QtGui

from ._qt_const import ICON_DIR

APPLICATION = None


def _get_ipython_shell():
    # check if IPython is imported
    if "IPython" in sys.modules:
        from IPython import get_ipython

        return get_ipython()
    return None


def gui_qt():
    """Call "%gui qt" magic."""
    shell = _get_ipython_shell()
    if shell and shell.active_eventloop != "qt":
        shell.enable_gui("qt")
    return None


def gui_qt_is_active() -> bool:
    """True only if "%gui qt" magic is called in ipython kernel."""
    shell = _get_ipython_shell()
    return shell and shell.active_eventloop == "qt"


def get_app():
    """Get QApplication."""
    global APPLICATION
    gui_qt()
    app = QApplication.instance()
    if app is None:
        if PYQT5:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
        app = QApplication([])

    if app.windowIcon().isNull():
        app.setWindowIcon(QtGui.QIcon(str(ICON_DIR / "window_icon.png")))
    app.setApplicationName("tabulous")
    APPLICATION = app
    return app


def run_app():
    """Start the event loop."""
    if not gui_qt_is_active():
        from tabulous.exceptions import ExceptionHandler

        with ExceptionHandler(hook=_excepthook) as _:
            get_app().exec_()
        return None


def _excepthook(exc_type: type[Exception], exc_value: Exception, exc_traceback):
    """Exception hook used during application execution."""
    from ._traceback import QtErrorMessageBox
    from ._mainwindow import QMainWindow

    viewer = QMainWindow.currentViewer()
    QtErrorMessageBox.raise_(exc_value, parent=viewer.native)
    return None
