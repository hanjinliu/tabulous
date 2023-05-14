import pytest

@pytest.fixture
def make_tabulous_viewer():
    from tabulous._utils import init_config
    from tabulous import TableViewer
    def func(show=False):
        return TableViewer(show=show)
    with init_config():
        yield func
