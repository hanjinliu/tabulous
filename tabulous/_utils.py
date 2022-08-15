from __future__ import annotations
from pathlib import Path

TXT_PATH = Path(__file__).parent / "_tabulous_history.txt"


def dump_file_open_path(path: str):
    try:
        if not TXT_PATH.exists():
            TXT_PATH.write_text("")
        with open(TXT_PATH, "r+") as f:
            lines = f.readlines() + [str(path)]
            if len(lines) > 16:
                lines = lines[-16:]
            f.truncate(0)
            f.write("\n".join(lines))
    except Exception as e:
        print(e)
    return None


def load_file_open_path() -> list[str]:
    if not TXT_PATH.exists():
        return []
    try:
        with open(TXT_PATH) as f:
            lines = f.readlines()
    except Exception as e:
        print(e)
        lines = []
    return lines
