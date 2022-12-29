from __future__ import annotations

from typing import Union, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
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
    if suf in (".csv", ".txt", ".dat"):
        df.to_csv(path)
    elif suf in (".xlsx", ".xls", "xml"):
        df.to_excel(path)
    elif suf in (".html",):
        df.to_html(path)
    elif suf in (".parquet", ".pq"):
        df.to_parquet(path)
    else:
        raise ValueError(f"Extension {suf} not supported.")


def _get_index_col(path: PathLike, sep=",") -> int | None:
    with open(path) as f:
        first_char = f.read(1)
    if first_char == sep:
        return 0
    return None
