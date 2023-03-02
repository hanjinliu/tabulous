from __future__ import annotations
from typing import Any
import re
import requests
from superqt.utils import thread_worker
import warnings


def get_latest_version() -> str:
    url = "https://pypi.org/pypi/tabulous/json"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to get latest version: {resp.status_code}")
    js = resp.json()
    release: dict[str, Any] = js["releases"]
    all_releases = list(release.keys())
    for r in reversed(all_releases):
        if re.match(r".*[a-zA-Z].*", r):
            continue
        return r
    return "0.0.0"


def get_current_version() -> str:
    from tabulous import __version__

    return __version__


@thread_worker
def _get_latest_version() -> str | None:
    try:
        version = get_latest_version()
        if get_current_version() >= version:
            version = None
    except Exception as e:
        warnings.warn(f"Failed to fetch latest version {type(e).__name__}: {e}")
        version = None
    return version


def get_worker():
    return _get_latest_version()
