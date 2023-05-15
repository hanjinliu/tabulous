from __future__ import annotations

from typing import TYPE_CHECKING
from io import StringIO

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase
    from tabulous.widgets._table import _DataFrameTableLayer


# This identifier is inaccessible from the console because it contains dots.
# It is only used from the local namespace dict.
VIEWER_IDENTIFIER = "__ipython.tabulous.viewer__"


def _get_viewer(ns: dict) -> TableViewerBase:
    """Return the viewer from the namespace."""
    viewer = ns.get(VIEWER_IDENTIFIER, None)
    if viewer is None:
        raise RuntimeError("Viewer not found in namespace")
    return viewer


def _filter_args(line: str) -> tuple[list[str], list[str]]:
    quot_flag_1 = False
    quot_flag_2 = False
    args: list[str] = []
    keywords: list[str] = []
    idx = 0
    for i, c in enumerate(line + " "):
        if c == " ":
            if not (quot_flag_1 or quot_flag_2) and (word := line[idx:i]):
                if word.startswith("-"):
                    keywords.append(word)
                else:
                    args.append(word)
                idx = i + 1
        elif c == '"':
            quot_flag_2 = not quot_flag_2
        elif c == "'":
            quot_flag_1 = not quot_flag_1

    return args, keywords


_INSTALLED = False


def install_magics():
    # magic commands can only be registered within a score where `get_ipython` is
    # available.
    global _INSTALLED

    if _INSTALLED:
        return

    from IPython import get_ipython  # noqa: F401
    from IPython.core.magic import (
        register_line_magic,
        register_cell_magic,
        register_line_cell_magic,
        needs_local_scope,
    )

    @register_line_magic
    @needs_local_scope
    def add(line: str, local_ns: dict = {}):
        """
        Add an object to the table viewer.

        Examples
        --------
        >>> %add df
        >>> %add df as table
        """
        viewer = _get_viewer(local_ns)
        if " as " in line:
            obj, typ = line.rsplit(" as ", maxsplit=1)
        else:
            obj = line.strip()
            typ = "table"
        if typ == "table":
            _add_fn = viewer.add_table
        elif typ == "spreadsheet":
            _add_fn = viewer.add_spreadsheet
        elif typ == "groupby":
            _add_fn = viewer.add_groupby
        elif typ == "loader":
            _add_fn = viewer.add_loader
        else:
            raise ValueError(
                f"Unknown type {typ}. Must be one of 'table', "
                "'spreadsheet', 'groupby', or 'loader'."
            )
        ns = local_ns.copy()
        ns["__builtins__"] = {}
        return _add_fn(eval(obj, ns, {}))

    @register_cell_magic
    @needs_local_scope
    def csv(line: str, cell: str | None = None, local_ns: dict = {}):
        """
        Convert a CSV string to a spreadsheet.

        Examples
        --------
        >>> viewer.add_spreadsheet(
        ...     {"a": [1, 4], "b": [2, 5], "c": [3, 6]},
        ...     name="my_table"
        ... )

        is identical to

        >>> %%table my_table
        >>> a b c
        >>> 1 2 3
        >>> 4 5 6

        """
        import pandas as pd

        if cell is None:
            raise ValueError("No input object provided")
        buf = StringIO(cell)
        df = pd.read_csv(buf)
        viewer = _get_viewer(local_ns)
        return viewer.add_spreadsheet(df, name=line)

    @register_line_magic
    @needs_local_scope
    def filter(line: str, local_ns: dict = {}):
        """
        Query-style filtration on a table.

        Examples
        --------
        >>> %filter a > 3  # equivalent to df.proxy.filter("a > 3")
        """
        viewer = _get_viewer(local_ns)
        if line == "":
            return viewer.current_table.proxy.filter(None)
        return viewer.current_table.proxy.filter(line, local_ns)

    @register_line_cell_magic
    @needs_local_scope
    def query(line: str, cell: str | None = None, local_ns: dict = {}):
        """
        Query-style evaluation on a table

        Examples
        --------
        >>> %query b = a + 1

        >>> %%query
        >>> b = a + 1
        >>> c = b > 3
        """
        viewer = _get_viewer(local_ns)
        table = viewer.current_table
        if table.table_type not in ("Table", "SpreadSheet"):
            raise ValueError("Querying is only supported for Tables and SpreadSheets")
        table: _DataFrameTableLayer
        if cell is not None:
            lines = cell.splitlines()
        else:
            lines = [line]
        for line in lines:
            line = line.strip()
            if line == "":
                continue
            table.query(line)

    @register_line_magic
    @needs_local_scope
    def plot(line: str, local_ns: dict = {}):
        viewer = _get_viewer(local_ns)
        table = viewer.current_table
        args, keys = _filter_args(line)
        if "-n" in keys or "--new" in keys:
            table.plt.new_widget()
        if "-c" in keys or "--clear" in keys:
            table.plt.cla()
        if len(args) == 0:
            return
        elif len(args) == 1:
            y = table[args[0]].data
            table.plt.plot(y)
        else:
            x = table[args[0]].data
            for yname in args[1:]:
                y = table[yname].data
                table.plt.plot(x, y)
        return

    @register_line_magic
    @needs_local_scope
    def scatter(line: str, local_ns: dict = {}):
        viewer = _get_viewer(local_ns)
        table = viewer.current_table
        args, keys = _filter_args(line)
        if "-n" in keys or "--new" in keys:
            table.plt.new_widget()
        if "-c" in keys or "--clear" in keys:
            table.plt.cla()
        if len(args) == 0:
            return
        elif len(args) == 1:
            raise ValueError("scatter requires at least two arguments (X and Y)")
        else:
            x = table[args[0]].data
            for yname in args[1:]:
                y = table[yname].data
                table.plt.scatter(x, y)
        return

    del add, csv, filter, query, plot, scatter
    _INSTALLED = True
    return None
