from __future__ import annotations

from typing import Union
from pathlib import Path
import pandas as pd

PathLike = Union[str, Path, bytes]


def open_file(path: PathLike) -> pd.DataFrame | dict[str, pd.DataFrame]:
    """
    Read a table data and add to the viewer.

    Parameters
    ----------
    path : path like
        File path.
    """
    import pandas as pd

    path = Path(path)
    suf = path.suffix

    if suf in (".csv", ".txt", ".dat"):
        df = pd.read_csv(path, index_col=_get_index_col(path))
    elif suf in (".xlsx", ".xls", ".xlsb", ".xlsm", ".xltm", "xltx", ".xml"):
        df: dict[str, pd.DataFrame] = pd.read_excel(path, sheet_name=None)
    elif suf in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Extension {suf!r} not supported.")
    return df


def save_file(path: PathLike, df: pd.DataFrame) -> None:
    """Save current table."""
    path = Path(path)
    suf = path.suffix
    # if index is not edited, do not save it
    index = type(df.index) is not pd.RangeIndex

    if suf in (".csv", ".txt", ".dat"):
        df.to_csv(path, index=index)
    elif suf in (".tsv",):
        df.to_csv(path, sep="\t", index=index)
    elif suf in (".xlsx", ".xls", "xml"):
        df.to_excel(path, index=index)
    elif suf in (".html",):
        df.to_html(path, index=index)
    elif suf in (".parquet", ".pq"):
        df.to_parquet(path, index=index)
    else:
        raise ValueError(f"Extension {suf} not supported.")


def _get_index_col(path: PathLike, sep=",") -> int | None:
    index_col = None
    try:
        with open(path) as f:
            first_char = f.read(1)
        if first_char == sep:
            index_col = 0
    except Exception:
        pass
    return index_col
