from __future__ import annotations
from typing import Callable
from .widgets import TableViewer
from functools import wraps
import pandas as pd

def _inject_pandas_signature(pd_func: Callable, return_annotation=None):
    def wrapper(f: Callable):
        out = wraps(pd_func)(f)
        out.__annotations__["return"] = return_annotation
        return out
    return wrapper
    

@_inject_pandas_signature(pd.read_csv, return_annotation=TableViewer)
def read_csv(*args, **kwargs):
    viewer = TableViewer(show=True)
    viewer.read_csv(*args, **kwargs)
    return viewer

@_inject_pandas_signature(pd.read_excel, return_annotation=TableViewer)
def read_excel(*args, **kwargs):
    viewer = TableViewer(show=True)
    viewer.read_excel(*args, **kwargs)
    return viewer
