from __future__ import annotations

from types import MappingProxyType
from typing import Any
from dataclasses import asdict, dataclass, field
from functools import wraps
from pathlib import Path
from appdirs import user_state_dir, user_config_dir


TXT_PATH = Path(user_state_dir("tabulous", "tabulous", "history.txt"))
CONFIG_PATH = Path(user_config_dir("tabulous", "tabulous", "config.toml"))
CELL_NAMESPACE_PATH = Path(user_state_dir("tabulous", "tabulous", "cell_namespace.py"))
SETTINGS_JSON = Path(user_state_dir("tabulous", "tabulous", "settings.json"))


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


@warn_on_exc(default=MappingProxyType({}))
def load_cell_namespace() -> MappingProxyType:
    """Load the cell namespace from a file."""
    if not CELL_NAMESPACE_PATH.exists():
        CELL_NAMESPACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CELL_NAMESPACE_PATH.write_text("")
    with open(CELL_NAMESPACE_PATH, encoding="utf-8") as f:
        code = compile(f.read(), CELL_NAMESPACE_PATH, "exec")
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

        console_namespace = tm.get("console_namespace", {})
        table = tm.get("table", {})
        cell = tm.get("cell", {})
        window = tm.get("window", {})
        if not (kb := tm.get("keybindings", {})):
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


def _as_fields(kwargs: dict[str, Any], dcls: type) -> dict[str, Any]:
    """Remove dict keys that does not belong to the dataclass fields."""
    fields = set(dcls.__annotations__.keys())
    return {k: v for k, v in kwargs.items() if k in fields}
