from __future__ import annotations

from types import MappingProxyType
from typing import Any
from dataclasses import asdict, dataclass, field
from functools import wraps
from pathlib import Path
from contextlib import contextmanager
from appdirs import user_config_dir


TXT_PATH = Path(user_config_dir("tabulous", "tabulous", "history.txt"))
CONFIG_PATH = Path(user_config_dir("tabulous", "tabulous", "config.toml"))
CELL_NAMESPACE_PATH = Path(user_config_dir("tabulous", "tabulous", "cell_namespace.py"))
POST_INIT_PATH = Path(user_config_dir("tabulous", "tabulous", "post_init.py"))


def warn_on_exc(default=None):
    def _wrapper(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                import warnings

                warnings.warn(f"{type(e).__name__}: {e}", UserWarning)
                return default

        return wrapper

    return _wrapper


@warn_on_exc(default=None)
def dump_file_open_path(path: str):
    """Save the recently opened file paths to a text file."""
    path = str(path)
    if not TXT_PATH.exists():
        TXT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TXT_PATH.write_text("")
    with open(TXT_PATH, "r+") as f:
        lines = [s.strip() for s in f.readlines()]
        if path in lines:
            lines.remove(path)
            lines.append(path)
        else:
            lines.append(path)
            if len(lines) > 16:
                lines = lines[-16:]
        f.truncate(0)
        f.seek(0)
        f.write("\n".join(lines))

    return None


@warn_on_exc(default=[])
def load_file_open_path() -> list[str]:
    """Load the recently opened file paths to a text file."""
    if not TXT_PATH.exists():
        return []
    with open(TXT_PATH) as f:
        lines = [s.strip() for s in f.readlines()]

    return lines


def _compile_file(path: Path, default_text: str = ""):
    # if file doesn't exist, create it
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    with open(path, encoding="utf-8") as f:
        code_str = f.read()
        code = compile(code_str, path, "exec")
    if code_str.strip() == "":
        path.write_text(default_text.strip() + "\n")
    return code


@warn_on_exc(default=MappingProxyType({}))
def load_cell_namespace() -> MappingProxyType:
    """Load the cell namespace from a file."""
    code = _compile_file(CELL_NAMESPACE_PATH, default_text=_CELL_NAMESPACE_TEXT)
    ns: dict[str, Any] = {}
    exec(code, {}, ns)
    to_be_deleted = set()
    for k in ns.keys():
        if k.startswith("_"):
            to_be_deleted.add(k)

    if "__all__" in to_be_deleted:
        _all = ns.get("__all__", [])
        to_be_deleted.update(_all)
    for k in to_be_deleted:
        ns.pop(k, None)
    return MappingProxyType(ns)


def get_post_initializers():
    code = _compile_file(POST_INIT_PATH, default_text=_POST_INIT_TEXT)
    ns: dict[str, Any] = {}
    exec(code, {}, ns)

    if len(ns) == 0:
        # if file is empty, don't do anything
        return None

    from tabulous.post_init import TableInitializer, ViewerInitializer

    table_initializer = TableInitializer()
    viewer_initializer = ViewerInitializer()
    for var in ns.values():
        if isinstance(var, TableInitializer):
            table_initializer.join(var)
        elif isinstance(var, ViewerInitializer):
            viewer_initializer.join(var)
    return viewer_initializer, table_initializer


def prep_default_keybindings() -> dict[str, str | list[str]]:
    from tabulous.commands import DEFAULT_KEYBINDING_SETTING

    kb = {}
    for cmd, seq in DEFAULT_KEYBINDING_SETTING:
        mod = cmd.__module__.split(".")[-1]
        name = cmd.__name__
        kb[f"{mod}.{name}"] = seq
    return kb


@dataclass
class ConsoleNamespace:
    """Default namespace of the console."""

    tabulous: str = "tbl"
    viewer: str = "viewer"
    pandas: str = "pd"
    numpy: str = "np"
    load_startup_file: bool = True


@dataclass
class Table:
    """Table settings."""

    max_row_count: int = 400000
    max_column_count: int = 40000
    font: str = "Arial"
    font_size: int = 10
    row_size: int = 28
    column_size: int = 100


@dataclass
class Cell:
    """Cell settings."""

    eval_prefix: str = "="
    ref_prefix: str = "&="


@dataclass
class Window:
    """Window config."""

    ask_on_close: bool = True
    show_console: bool = False
    theme: str = "light-blue"
    notify_latest: bool = True
    selection_editor: bool = True
    title_bar: str = "native"


@dataclass
class TabulousConfig:
    """The config model."""

    console_namespace: ConsoleNamespace = field(default_factory=ConsoleNamespace)
    table: Table = field(default_factory=Table)
    cell: Cell = field(default_factory=Cell)
    window: Window = field(default_factory=Window)
    keybindings: dict[str, str | list[str]] = field(
        default_factory=prep_default_keybindings
    )

    @classmethod
    def from_toml(cls, path: Path = CONFIG_PATH) -> TabulousConfig:
        """Load the config file."""
        import toml

        if not path.exists():
            return cls()

        with open(path) as f:
            tm = toml.load(f)
        return cls.from_dict(tm)

    @classmethod
    def from_dict(cls, dict_: dict[str, Any]) -> TabulousConfig:
        console_namespace = dict_.get("console_namespace", {})
        table = dict_.get("table", {})
        cell = dict_.get("cell", {})
        window = dict_.get("window", {})
        if not (kb := dict_.get("keybindings", {})):
            kb = prep_default_keybindings()
        return cls(
            ConsoleNamespace(**_as_fields(console_namespace, ConsoleNamespace)),
            Table(**_as_fields(table, Table)),
            Cell(**_as_fields(cell, Cell)),
            Window(**_as_fields(window, Window)),
            kb,
        )

    def as_toml(self):
        """Save the config file."""
        import toml

        if not CONFIG_PATH.exists():
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text("")
        with open(CONFIG_PATH, "w") as f:
            toml.dump(asdict(self), f)

        return None

    def as_immutable(self) -> MappingProxyType:
        """Return the immutable version of the config."""
        return MappingProxyType(
            {k: MappingProxyType(v) for k, v in asdict(self).items()}
        )


CONFIG: TabulousConfig | None = None


def get_config(reload: bool = False) -> TabulousConfig:
    """Get the global config."""
    global CONFIG
    if CONFIG is None or reload:
        CONFIG = TabulousConfig.from_toml()
    return CONFIG


def update_config(cfg: TabulousConfig, save: bool = False) -> None:
    """Update the global config."""
    global CONFIG
    CONFIG = cfg
    if save:
        CONFIG.as_toml()
    return None


@contextmanager
def init_config():
    global CONFIG
    ori = TabulousConfig()
    old = CONFIG
    CONFIG = ori
    try:
        yield
    finally:
        CONFIG = old


def _as_fields(kwargs: dict[str, Any], dcls: type) -> dict[str, Any]:
    """Remove dict keys that does not belong to the dataclass fields."""
    fields = set(dcls.__annotations__.keys())
    return {k: v for k, v in kwargs.items() if k in fields}


_CELL_NAMESPACE_TEXT = """
# File for custom namespace in the table cells.

# Variables defined in the `__all__` list will be available in the cells.
# By, uncommenting following lines, you can use such as
# `=SUM(df.iloc[:, 0])` in cells.

# import scipy
# import numpy as np

# __all__ = ["scipy", "SUM", "AVERAGE"]

# def SUM(x):
#     return np.sum(x)

# def AVERAGE(x):
#     return np.mean(x)
"""

_POST_INIT_TEXT = """
# File for post-initialization of the viewer and table.
# You can add custom actions, commands and variables on the startup of the
# application.

# First, get initializer objects.

# from tabulous.post_init import get_initializers
# viewer, table = get_initializers()

# These objects has similar interface to the viewer and table classes.

# 1. Add custom actions to the right-click context menu of table columns.

# @table.columns.register("User defined > Print column name")
# def _print_column_name(table, index):
#     print(table.columns[index])

# 2. Add custom keybindings to viewers and tables.

# @viewer.keymap.register("Ctrl+K, Ctrl+1")
# def _my_keybinding(viewer):
#     print(viewer)

# @table.keymap.register("Ctrl+Shift+K, Ctrl+1")
# def _my_keybinding(table):
#     print(table)

# 3. Add custom variables to the console (note that you can also update
#    the IPython startup files to do the same thing).

# viewer.console.update({"PI": 3.141592653589793})

# 4. Add custom variables to the table cells (not that you can also update
#    the cell_namespace.py file to do the same thing).

# import numpy as np
# viewer.cell_namespace.update({"SUM": np.sum})

"""
