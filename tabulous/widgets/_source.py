from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
from dataclasses import dataclass
import weakref

if TYPE_CHECKING:
    from tabulous.widgets._table import TableBase


@dataclass(frozen=True)
class Source:
    """Class that describes source info of a table."""

    path: Path | None = None
    parent: weakref.ReferenceType[TableBase] | None = None

    @classmethod
    def from_table(self, table: TableBase) -> Source:
        return Source(parent=weakref.ref(table))

    def get_parent(self) -> TableBase | None:
        if self.parent is not None:
            return self.parent()
        return None
