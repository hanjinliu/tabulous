import pytest

@pytest.fixture
def make_tabulous_viewer():
    from tabulous import TableViewer
    def func(show=False):
        return TableViewer(show=show)
    yield func

@pytest.fixture(scope="session", autouse=True)
def session():
    from tabulous._utils import init_config, update_config, get_config
    with init_config():
        cfg = get_config()
        cfg.window.animate = False
        update_config(cfg, save=True)
        yield
