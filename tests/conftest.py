import pytest
from weakref import WeakSet
from typing import Literal

@pytest.fixture
def make_tabulous_viewer(qtbot):
    from tabulous import TableViewer, TableViewerWidget, MagicTableViewer
    from tabulous.widgets import TableViewerBase

    viewers: WeakSet[TableViewerBase] = WeakSet()
    def factory(
        cls: Literal["main", "widget", "magic"] = "main",
        show: bool = False,
    ):
        if cls == "main":
            viewer = TableViewer(show=show)
        elif cls == "widget":
            viewer = TableViewerWidget(show=show)
        elif cls == "magic":
            viewer = MagicTableViewer(show=show)
        else:
            raise ValueError(f"Invalid input {cls!r}")
        viewers.add(viewer)
        return viewer

    yield factory

    for viewer in viewers:
        viewer.close()
        viewer.native.deleteLater()

@pytest.fixture(scope="session", autouse=True)
def session():
    from tabulous._utils import init_config, update_config, get_config
    from tabulous._qt._mainwindow import QMainWindow
    from qtpy.QtWidgets import QApplication
    import gc

    with init_config():
        cfg = get_config()
        # disable animations
        cfg.window.animate = False
        # disable "Are you sure you want to quit?" dialog
        cfg.window.ask_on_close = False
        # disable latest version notification
        cfg.window.notify_latest = False
        # do not launch qtconsole
        cfg.window.show_console = False
        update_config(cfg, save=True)
        yield

    for instance in QMainWindow._instances:
        instance.close()
        instance.deleteLater()

    QApplication.closeAllWindows()
    QMainWindow._instances.clear()
    N_PROCESS_EVENTS = 50
    for _ in range(N_PROCESS_EVENTS):
        QApplication.processEvents()
    gc.collect()
    if QMainWindow._instances:
        raise RuntimeError("QMainWindow instances not cleaned up!")
    QMainWindow._instances.clear()
