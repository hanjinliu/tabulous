from __future__ import annotations
from pathlib import Path
from appdirs import user_state_dir

TXT_PATH = Path(user_state_dir("tabulous", "tabulous", "history.txt"))
SETTING_PATH = Path(user_state_dir("tabulous", "tabulous", "setting.yaml"))


def dump_file_open_path(path: str):
    path = str(path)
    try:
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

    except Exception as e:
        _warn_exc(e)
    return None


def load_file_open_path() -> list[str]:
    if not TXT_PATH.exists():
        return []
    try:
        with open(TXT_PATH) as f:
            lines = [s.strip() for s in f.readlines()]
    except Exception as e:
        _warn_exc(e)
        lines = []
    return lines


def dump_setting(js: dict):
    import yaml

    try:
        if not SETTING_PATH.exists():
            SETTING_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTING_PATH.write_text("")
        with open(SETTING_PATH, "r+") as f:
            yaml.dump(js, f)

    except Exception as e:
        _warn_exc(e)
    return None


def load_setting() -> dict:
    import yaml

    if not SETTING_PATH.exists():
        return {}
    try:
        with open(SETTING_PATH) as f:
            js = yaml.load(f, Loader=yaml.FullLoader)
    except Exception as e:
        _warn_exc(e)
        js = {}
    return js


def _warn_exc(e: Exception) -> None:
    import warnings

    return warnings.warn(f"{type(e).__name__}: {e}", UserWarning)
