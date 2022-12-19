from __future__ import annotations
from typing import TYPE_CHECKING
from . import _dialogs, _utils

if TYPE_CHECKING:
    from tabulous.widgets import TableViewerBase


def show_keymap(viewer: TableViewerBase):
    """Show key map widget"""
    viewer._qwidget.showKeyMap()


def close_window(viewer: TableViewerBase):
    """Close window"""
    viewer._qwidget.close()


def new_window(viewer: TableViewerBase):
    """Create a new window"""
    new = viewer.__class__()
    return new._qwidget.activateWindow()


def toggle_toolbar(viewer: TableViewerBase):
    """Toggle toolbar visibility"""
    viewer._qwidget.toggleToolBarVisibility()


def toggle_console(viewer: TableViewerBase):
    """Toggle QtConsole visibility"""
    return viewer._qwidget.toggleConsoleVisibility()


def toggle_fullscreen(viewer: TableViewerBase):
    """Toggle fullscreen"""
    if viewer._qwidget.isFullScreen():
        viewer._qwidget.showNormal()
    else:
        viewer._qwidget.showFullScreen()


def show_command_palette(viewer: TableViewerBase):
    """Show the command palette."""
    viewer._qwidget.showCommandPalette()


def focus_table(viewer: TableViewerBase):
    """Move focus to the table."""
    viewer.native.setCellFocus()


def toggle_focus(viewer: TableViewerBase):
    """Toggle focus between table and command palette."""
    table = viewer.current_table
    qviewer = viewer._qwidget
    if table is None:
        return
    if table._qwidget._qtable_view.hasFocus():
        console = qviewer._console_widget
        if console is not None and console.isActive():
            console.setFocus()
    else:
        qviewer.setCellFocus()
    return
