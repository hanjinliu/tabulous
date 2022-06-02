from __future__ import annotations
from .widgets import TableViewer
from functools import wraps
import pandas as pd

@wraps(pd.read_csv)
def read_csv(*args, **kwargs):
    viewer = TableViewer(show=True)
    return viewer.read_csv(*args, **kwargs)

@wraps(pd.read_excel)
def read_excel(*args, **kwargs):
    viewer = TableViewer(show=True)
    return viewer.read_excel(*args, **kwargs)
