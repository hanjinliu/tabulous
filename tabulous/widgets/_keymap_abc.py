from __future__ import annotations

from abc import ABC
from ._component import KeyMap


class SupportKeyMap(ABC):
    """Object that supports keymap."""

    keymap = KeyMap()
