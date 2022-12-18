from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def show_keymap(viewer: TableViewerBase):
    """Show the widget to search for key bindings."""
    viewer._qwidget.showKeyMap()


def close_window(viewer: TableViewerBase):
    """Close this window."""
    viewer._qwidget.close()


def new_window(viewer: TableViewerBase):
    """Create a new window."""
    new = viewer.__class__()
    return new._qwidget.activateWindow()


def toggle_toolbar(viewer: TableViewerBase):
    """Show or collapse the toolbar."""
    viewer._qwidget.toggleToolBarVisibility()


def toggle_fullscreen(viewer: TableViewerBase):
    """Enable or disable fullscreen mode."""
    if viewer._qwidget.isFullScreen():
        viewer._qwidget.showNormal()
    else:
        viewer._qwidget.showFullScreen()


def show_command_palette(viewer: TableViewerBase):
    """Show the command palette."""
    viewer._qwidget.showCommandPalette()
