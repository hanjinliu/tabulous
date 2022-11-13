from __future__ import annotations
from pathlib import Path
from enum import Enum
from typing import Callable, Literal, overload
from qtpy import QtWidgets as QtW, QtCore
from .._utils import load_file_open_path

# Modified from magicgui
# See https://github.com/pyapp-kit/magicgui/blob/main/magicgui/backends/_qtpy/widgets.py
class FileDialogMode(Enum):
    """FileDialog mode options."""

    EXISTING_FILE = "r"
    EXISTING_FILES = "rm"
    OPTIONAL_FILE = "w"
    EXISTING_DIRECTORY = "d"


QFILE_DIALOG_MODES: dict[FileDialogMode, Callable] = {
    FileDialogMode.EXISTING_FILE: QtW.QFileDialog.getOpenFileName,
    FileDialogMode.EXISTING_FILES: QtW.QFileDialog.getOpenFileNames,
    FileDialogMode.OPTIONAL_FILE: QtW.QFileDialog.getSaveFileName,
    FileDialogMode.EXISTING_DIRECTORY: QtW.QFileDialog.getExistingDirectory,
}


class QtFileHistoryManager(QtCore.QObject):
    def __init__(
        self,
        default_path: Path | str | bytes | None = None,
    ):
        super().__init__()
        self._hist: list[Path] = [Path(path.strip()) for path in load_file_open_path()]
        self.default_path = default_path or Path.cwd()
        self._instances: dict[int, QtFileHistoryManager] = {}
        self._parent_class = None

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        _id = id(obj)
        if (out := self._instances.get(_id, None)) is None:
            out = self.__class__(default_path=self.default_path)
            if self._parent_class is not None and issubclass(
                self._parent_class, QtCore.QObject
            ):
                out.setParent(obj)
            self._instances[_id] = out
        return out

    def __set_name__(self, owner: type | None, name: str):
        self._parent_class = owner

    def recentlyVisitedDirectory(self) -> Path:
        """Return the mose recently visited, existing directory."""
        for path in reversed(self._hist):
            if path.exists():
                return path

        return self.default_path

    @overload
    def openFileDialog(
        self,
        mode: Literal[
            "r",
            "w",
            "d",
            FileDialogMode.EXISTING_FILE,
            FileDialogMode.OPTIONAL_FILE,
            FileDialogMode.EXISTING_DIRECTORY,
        ],
        caption: str | None = None,
        filter: str | None = None,
    ) -> Path | None:
        ...

    @overload
    def openFileDialog(
        self,
        mode: Literal["rm"] | Literal[FileDialogMode.EXISTING_FILES],
        caption: str | None = None,
        filter: str | None = None,
    ) -> list[Path] | None:
        ...

    def openFileDialog(
        self,
        mode=FileDialogMode.EXISTING_FILE,
        caption=None,
        filter=None,
    ):
        if not isinstance(parent := self.parent(), QtW.QWidget):
            parent = None
        out = QFILE_DIALOG_MODES[FileDialogMode(mode)](
            parent=parent,
            caption=caption,
            directory=str(self.recentlyVisitedDirectory()),
            filter=filter,
        )
        if out is None:
            return None

        if mode is FileDialogMode.EXISTING_DIRECTORY:
            path = out
        else:
            path, _ = out

        if isinstance(path, str):
            if path != "":
                out = Path(path)
                if out.is_file():
                    self._hist.append(out.parent)
                else:
                    self._hist.append(out)
            else:
                out = None
        elif isinstance(path, list):
            if len(path) > 0:
                out = [Path(p) for p in path]
                self._hist.append(out[-1])
            else:
                out = []
        else:
            out = None
        return out

    def clearHistory(self):
        """Clear the history of visited directories."""
        return self._hist.clear()

    def defaultPath(self) -> Path:
        """Get the default path."""
        return self._default_path

    def setDefaultPath(self, path: Path | str | bytes):
        """Set the default path."""
        path = Path(path)
        if not path.exists():
            raise ValueError(f"Path {path!r} does not exist.")
        self._default_path = path
