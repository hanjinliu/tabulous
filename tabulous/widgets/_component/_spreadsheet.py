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
    from tabulous.widgets._table import SpreadSheet  # noqa: F401

    _DtypeLike = Union[ExtensionDtype, np.dtype]

T = TypeVar("T")


class ColumnDtypeInterface(
    Component["SpreadSheet"], MutableMapping[Hashable, "_DtypeLike"]
):
    """Interface to the column dtype of spreadsheet."""

    def _get_dtype_map(self):
        return self.parent._qwidget._columns_dtype

    def __getitem__(self, key: Hashable) -> _DtypeLike | None:
        """Get the dtype of the given column name."""
        return self._get_dtype_map().get(key, None)

    def __setitem__(self, key: Hashable, dtype: Any) -> None:
        """Set a dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, dtype)

    def __delitem__(self, key: Hashable) -> None:
        """Reset the dtype to the given column name."""
        return self.parent._qwidget.setColumnDtype(key, None)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        _args = ",\n\t".join(f"{k!r}: {v}" for k, v in self._get_dtype_map().items())
        return f"{clsname}(\n\t{_args}\n)"

    def __len__(self) -> str:
        return len(self._get_dtype_map())

    def __iter__(self) -> Iterator[Hashable]:
        return iter(self._get_dtype_map())

    def set(
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

    set_dtype = set
