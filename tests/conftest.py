import pytest
from weakref import WeakSet
import gc

@pytest.fixture
def make_tabulous_viewer(qtbot):
    from tabulous import TableViewer

    viewers: WeakSet[TableViewer] = WeakSet()

    def factory(show=False):
        viewer = TableViewer(show=show)
        viewers.add(viewer)
        return viewer

    yield factory

    for viewer in viewers:
        viewer._unlink_events()
        viewer.close()
        viewer.native.deleteLater()


@pytest.fixture(scope="session", autouse=True)
def session():
    from tabulous._utils import init_config, update_config, get_config
    from tabulous._qt._mainwindow import QMainWindow
    from qtpy.QtWidgets import QApplication

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
