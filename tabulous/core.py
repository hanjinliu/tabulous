from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from .widgets import TableViewer

if TYPE_CHECKING:
    from .widgets.mainwindow import _TableViewerBase

CURRENT_VIEWER: _TableViewerBase | None = None


def current_viewer() -> _TableViewerBase:
    """Get the current table viewer widget."""
    global CURRENT_VIEWER
    if CURRENT_VIEWER is None:
        CURRENT_VIEWER = TableViewer()
    return CURRENT_VIEWER


def set_current_viewer(viewer: _TableViewerBase) -> _TableViewerBase:
    """Set a table viewer as the current one."""
    global CURRENT_VIEWER
    from .widgets.mainwindow import _TableViewerBase

    if not isinstance(viewer, _TableViewerBase):
        raise TypeError(f"Cannot set {type(viewer)} as the current viewer.")
    CURRENT_VIEWER = viewer
    return viewer


def read_csv(path: str | Path, *args, **kwargs) -> _TableViewerBase:
    import pandas as pd

    df = pd.read_csv(path, *args, **kwargs)
    name = Path(path).stem
    viewer = current_viewer()
    viewer.add_table(df, name=name)
    return viewer


def read_excel(path: str | Path, *args, **kwargs) -> _TableViewerBase:
    import pandas as pd

    df_dict: dict[str, pd.DataFrame] = pd.read_excel(
        path, *args, sheet_name=None, **kwargs
    )

    viewer = current_viewer()
    for sheet_name, df in df_dict.items():
        viewer.add_table(df, name=sheet_name)
    return viewer


def view_table(
    data,
    *,
    name: str | None = None,
    editable: bool = False,
    copy: bool = True,
) -> _TableViewerBase:
    viewer = current_viewer()
    viewer.add_table(data, name=name, editable=editable, copy=copy)
    return viewer


def view_spreadsheet(
    data,
    *,
    name: str | None = None,
    editable: bool = True,
    copy: bool = True,
) -> _TableViewerBase:
    viewer = current_viewer()
    viewer.add_spreadsheet(data, name=name, editable=editable, copy=copy)
    return viewer


def open_sample(
    sample_name: str,
    plugin_name: str = "seaborn",
) -> _TableViewerBase:
    viewer = current_viewer()
    viewer.open_sample(sample_name, plugin_name)
    return viewer


def run():
    """Run event loop."""
    from ._qt._app import run_app

    run_app()
