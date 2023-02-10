# This file is used to generate the readme/documentation for tabulous.
from __future__ import annotations

from pathlib import Path
from typing import Callable, Union

from tabulous import TableViewer
from tabulous.widgets import TableBase

_Registerable = Callable[[], Union[TableBase, TableViewer]]


class FunctionRegistry:
    def __init__(self, root: str | Path):
        self._root = Path(root)
        self._all_functions: list[_Registerable] = []

    def register(self, f: _Registerable):
        def wrapped():
            if out := f():
                out.save_screenshot(self._root / f"{f.__name__}.png")
                if isinstance(out, TableViewer):
                    out.close()

        self._all_functions.append(wrapped)
        return wrapped

    def run_all(self):
        for f in self._all_functions:
            f()
