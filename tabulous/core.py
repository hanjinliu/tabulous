from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING
from .widgets import TableViewer

CURRENT_VIEWER = None

def current_viewer():
    global CURRENT_VIEWER
    if CURRENT_VIEWER is None:
        CURRENT_VIEWER = TableViewer()
    return CURRENT_VIEWER

def set_current_viewer(viewer: TableViewer):
    global CURRENT_VIEWER
    CURRENT_VIEWER = viewer
    return viewer

def read_csv(path: str | Path, *args, **kwargs):
    import pandas as pd
    df = pd.read_csv(path, *args, **kwargs)
    name = Path(path).stem
    viewer = current_viewer()
    viewer.add_table(df, name=name)
    return viewer

def read_excel(path: str | Path, *args, **kwargs):
    import pandas as pd
    df_dict = pd.read_excel(path, *args, **kwargs)
    
    viewer = current_viewer()
    for sheet_name, df in df_dict.items():
        viewer.add_table(df, name=sheet_name)
    return viewer
