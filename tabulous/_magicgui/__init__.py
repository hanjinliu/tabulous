from ._table import MagicTableViewer
from ._register import (
    find_table_viewer_ancestor,
    find_current_table,
)
from ._selection import SelectionWidget
from ._dialog import dialog_factory, dialog_factory_mpl
from ._color_edit import ColorEdit
from ._toggle_switch import ToggleSwitch, ToggleSwitches, ToggleSwitchSelect

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.axes import Axes
else:
    from typing import Any

    Axes = Any

__all__ = [
    "MagicTableViewer",
    "find_table_viewer_ancestor",
    "find_current_table",
    "SelectionWidget",
    "dialog_factory",
    "dialog_factory_mpl",
    "ColorEdit",
    "ToggleSwitch",
    "ToggleSwitches",
    "ToggleSwitchSelect",
    "Axes",
]
