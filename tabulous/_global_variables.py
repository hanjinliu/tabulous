# This file is a container of global variables used in the tabulous package.


class table:
    """Default table settings."""

    max_row_count = 100000
    max_column_count = 100000
    font = "Arial"
    font_size = 10
    row_size = 28
    column_size = 100


class default_namespace:
    """Default name space for embedded console"""

    tabulous = "tbl"
    viewer = "viewer"
    pandas = "pd"
    numpy = "np"
    data = "DATA"
