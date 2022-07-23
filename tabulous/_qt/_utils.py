from __future__ import annotations
from typing import Callable
from qtpy.QtWidgets import QMessageBox, QAction
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from enum import Enum
from functools import reduce
from operator import or_


class MessageBoxMode(Enum):
    ERROR = "error"
    WARNING = "warn"
    INFO = "info"
    QUESTION = "question"
    ABOUT = "about"


_QMESSAGE_MODES = {
    MessageBoxMode.ERROR: QMessageBox.critical,
    MessageBoxMode.WARNING: QMessageBox.warning,
    MessageBoxMode.INFO: QMessageBox.information,
    MessageBoxMode.QUESTION: QMessageBox.question,
    MessageBoxMode.ABOUT: QMessageBox.about,
}


def show_messagebox(
    mode: str | MessageBoxMode = MessageBoxMode.INFO,
    title: str = None,
    text: str = None,
    parent=None,
) -> bool:
    """
    Freeze the GUI and open a messagebox dialog.

    Parameters
    ----------
    mode : str or MessageBoxMode, default is MessageBoxMode.INFO
        Mode of message box. Must be "error", "warn", "info", "question" or "about".
    title : str, optional
        Title of messagebox.
    text : str, optional
        Text in messagebox.
    parent : QWidget, optional
        Parent widget.

    Returns
    -------
    bool
        If "OK" or "Yes" is clicked, return True. Otherwise return False.
    """
    show_dialog = _QMESSAGE_MODES[MessageBoxMode(mode)]
    result = show_dialog(parent, title, text)
    return result in (QMessageBox.Ok, QMessageBox.Yes)


def to_action(f: Callable, parent=None) -> QAction:
    action = QAction(f.__name__.replace("_", " "), parent)
    action.triggered.connect(f)
    return action


def search_name_from_qmenu(qmenu: QtW.QMenu | QtW.QMenuBar, name: str):
    for a in qmenu.children():
        if isinstance(a, QAction) and a.text() == name:
            return a
    return None


_MODIFIERS = {
    "Shift": Qt.KeyboardModifier.ShiftModifier,
    "Ctrl": Qt.KeyboardModifier.ControlModifier,
    "Control": Qt.KeyboardModifier.ControlModifier,
    "Alt": Qt.KeyboardModifier.AltModifier,
    "Meta": Qt.KeyboardModifier.MetaModifier,
}


class QtKeys:
    """A custom class for handling key events."""

    def __init__(self, e: QtGui.QKeyEvent):
        self.modifier = e.modifiers()
        self.key = e.key()

    def __eq__(self, other):
        if isinstance(other, QtKeys):
            return self.modifier == other.modifier and self.key == other.key
        elif isinstance(other, str):
            *mods, btn = other.split("+")
            if not mods:
                qtmod = Qt.KeyboardModifier.NoModifier
            else:
                qtmod = reduce(or_, [_MODIFIERS[m] for m in mods])
            qtkey = getattr(Qt.Key, f"Key_{btn}")
            return self.modifier == qtmod and self.key == qtkey
        else:
            raise TypeError

    def is_typing(self) -> bool:
        """True if key is a letter or number."""
        return (
            self.modifier
            in (
                Qt.KeyboardModifier.NoModifier,
                Qt.KeyboardModifier.ShiftModifier,
            )
            and (Qt.Key.Key_Exclam <= self.key <= Qt.Key.Key_ydiaeresis)
        )

    def key_string(self) -> str:
        """Get clicked key in string form."""
        return QtGui.QKeySequence(self.key).toString()

    def has_ctrl(self) -> bool:
        """True if Ctrl is pressed."""
        return self.modifier & Qt.KeyboardModifier.ControlModifier

    def has_shift(self) -> bool:
        """True if Shift is pressed."""
        return self.modifier & Qt.KeyboardModifier.ShiftModifier
