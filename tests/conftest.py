import pytest
from tabulous._utils import init_config
from tabulous import TableViewer

@pytest.fixture
def make_tabulous_viewer():
    def func(show=False):
        return TableViewer(show=show)
    with init_config():
        yield func
