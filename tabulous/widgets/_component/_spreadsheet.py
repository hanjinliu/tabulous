from __future__ import annotations
from typing import (
    Hashable,
    TYPE_CHECKING,
    TypeVar,
    Any,
    Union,
    MutableMapping,
    Iterator,
)

import numpy as np
from ._base import Component

if TYPE_CHECKING:
    from pandas.core.dtypes.dtypes import ExtensionDtype
    from tabulous.widgets._table import SpreadSheet

    _DtypeLike = Union[ExtensionDtype, np.dtype]

T = TypeVar("T")


class ColumnDtypeInterface(
    Component["SpreadSheet"], MutableMapping[Hashable, "_DtypeLike"]
):
    """Interface to the column dtype of spreadsheet."""

    def __getitem__(self, key: Hashable) -> _DtypeLike | None:
        """Get the dtype of the given column name."""
        return self.parent._qwidget._columns_dtype.get(key, None)

    def __setitem__(self, key: Hashable, dtype: Any) -> None:
        """Set a dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, dtype)

    def __delitem__(self, key: Hashable) -> None:
        """Reset the dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        dict = self.parent._qwidget._columns_dtype
        return f"{clsname}({dict!r})"

    def __len__(self) -> str:
        return len(self.parent._qwidget._columns_dtype)

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self.parent._qwidget._columns_dtype)

    def set_dtype(
        self,
        name: Hashable,
        dtype: Any,
        *,
        validation: bool = True,
        formatting: bool = True,
    ) -> None:
        """Set dtype and optionally default validator and formatter."""
        self.parent._qwidget.setColumnDtype(name, dtype)
        if validation:
            self.parent._qwidget._set_default_data_validator(name)
        if formatting:
            self.parent._qwidget._set_default_text_formatter(name)
        return None
