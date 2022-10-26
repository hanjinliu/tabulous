from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import wraps
from pathlib import Path
from appdirs import user_state_dir, user_config_dir

TXT_PATH = Path(user_state_dir("tabulous", "tabulous", "history.txt"))
CONFIG_PATH = Path(user_config_dir("tabulous", "tabulous", "config.toml"))


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


@dataclass
class ConsoleNamespace:
    """Default namespace of the console."""

    tabulous: str = "tbl"
    viewer: str = "viewer"
    pandas: str = "pd"
    numpy: str = "np"
    data: str = "DATA"


@dataclass
class Table:
    """Table settings."""

    max_row_count: int = 100000
    max_column_count: int = 100000
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


@dataclass
class TabulousConfig:
    """The config model."""

    console_namespace: ConsoleNamespace = ConsoleNamespace()
    table: Table = Table()
    cell: Cell = Cell()
    window: Window = Window()

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
        return cls(
            ConsoleNamespace(**console_namespace),
            Table(**table),
            Cell(**cell),
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

    def as_immutable(self):
        from types import MappingProxyType

        return MappingProxyType(
            {k: MappingProxyType(asdict(v)) for k, v in asdict(self).items()}
        )


CONFIG: TabulousConfig | None = None


def get_config():
    global CONFIG
    if CONFIG is None:
        CONFIG = TabulousConfig.from_toml()
    return CONFIG
