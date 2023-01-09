==========================
Field Attributes of Tables
==========================

.. contents:: Contents
    :local:
    :depth: 1

.. include:: ../font.rst

Table operations are very complicated. Providing all the programmatic operations
to interact with table state and data as table methods is confusing. Thus, in
:mod:`tabulous`, these operations are well organized with fields and sub-fields
(For instance, all the methods related to table cells are all in :attr:`cell`
field).

Followings are all the fields that are available in table widgets.

``cell`` field
--------------

The :attr:`cell` field provides several methods to get access to table cells.

.. code-block:: python

    table.cell[1, 2] = -1
    table.cell[1, 0:5] = [1, 2, 3, 4, 5]

:attr:`cell` supports custom contextmenu registration. See :doc:`register_action`
for more detail.

.. note::

    To set new table data, :attr:`loc` and :attr:`iloc` is not safe.

    .. code-block:: python

        table.data.iloc[1, 2] = -1  # set new data

    This is not equivalent to editing cells directly for several reasons.

    - :class:`Table` data will be updated in this way but :class:`SpreadSheet` will not since
      the returned data is a copy.
    - :attr:`loc` and :attr:`iloc` does not check data type.
    - Table will not be updated immediately.

The :attr:`cell` field has several sub-fields.

``cell.ref``
^^^^^^^^^^^^

All the in-cell functions with cell references are accessible via :attr:`ref` sub-field.

.. code-block:: python

    table = viewer.add_spreadsheet(np.arange(10))
    table.cell[0, 1] = "&=np.mean(df.iloc[:, 0])"
    print(table.cell.ref[0, 1])  # get the slot function at (0, 1)
    print(table.cell.ref[1, 1])  # KeyError

``cell.label``
^^^^^^^^^^^^^^

Cell labels can be edited programmatically using this sub-field.

.. code-block:: python

    print(table.cell.label[0, 1])
    table.cell.label[0, 1] = "mean:"

``cell.text``
^^^^^^^^^^^^^

Displayed (formatted) text in cells can be obtained using this sub-field.

.. code-block:: python

    print(table.cell.text[0, 1])

``cell.text_color``
^^^^^^^^^^^^^^^^^^^

Displayed text color (8-bit RGBA) in cells can be obtained using this sub-field.

.. code-block:: python

    print(table.cell.text_color[0, 1])

``cell.background_color``
^^^^^^^^^^^^^^^^^^^^^^^^^

Displayed background color (8-bit RGBA) in cells can be obtained using this sub-field.

.. code-block:: python

    print(table.cell.text_color[0, 1])

``plt`` field
-------------

Since plotting is a common use case for table data analysis, plot canvases are implemented
by default. The basic plot functions are available in :attr:`plt` field with the
similar API as :mod:`matplotlib.pyplot` module.

.. code-block:: python

    table = viewer.tables[0]
    table.plt.plot(x, y)
    table.plt.hist(x)
    table.plt.scatter(x, y)

.. note::

    You can also update plot canvas from the "Plot" tab of the toolbar.


``index`` / ``columns`` field
-----------------------------

:attr:`index` and :attr:`column` behaves very similar to :attr:`index` and :attr:`column`
of :class:`pandas.DataFrame`.

.. code-block:: python

    # get header data
    print(table.index[1])
    print(table.columns[2])

    # get index of header name
    table.index.get_loc("index_name")
    table.columns.get_loc("column_name")

    # update header data
    table.index[1] = "index_name"
    table.columns[2] = "column_name"

:attr:`index` and `columns` support custom contextmenu registration. See
:doc:`register_action` for more detail.

``proxy`` field
---------------

Proxy includes sorting and filtering, that is, deciding which rows to be shown and
which not to be.

.. code-block:: python

    table.proxy.filter("label == 'A'")  # filter by 'label' column
    table.proxy.sort("value")  # sort by 'value' column
    table.reset()  # reset proxy

See :doc:`sort_filter` for more details.

``text_color`` / ``background_color`` field
-------------------------------------------

:attr:`text_color` and :attr:`background_color` stores all the column-specific colormaps.

.. code-block:: python

    table.text_color["A"]  # get the colormap of column "A"
    table.text_color["A"] = cmap  # set a colormap to column "A"

    # set a colormap to column "A" with a decorator
    @table.text_color.set("A")
    def cmap(x):
        ...

    del table.text_color["A"]  # reset the colormap defined for column "A"

See :doc:`columnwise_settings` for more details.

``formatter`` / ``validator`` field
-----------------------------------

:attr:`formatter` and :attr:`validator` stores all the column-specific text formatter
and data validator functions.

.. code-block:: python

    table.formatter["A"]  # get the formatter of column "A"
    table.formatter["A"] = "{:2f} cm"  # set a formatter of column "A"

    # set a formatter of column "A" with a decorator
    @table.formatter.set("A")
    def fmt(x):
        return f"{:2f} cm"

    del table.formatter["A"]  # reset the formatter of column "A"

See :doc:`columnwise_settings` for more details.

``dtypes`` field
----------------

:attr:`dtypes` is a :class:`SpreadSheet`-specific field. Since a spreadsheet has to
determine the data type of each column, you may occasionally want to tell which
data type it should be. This is especially important when a column should be
interpreted as ``category`` or ``datetime``.

:attr:`dtypes` is a ``dict``-like object that maps column names to data types.

.. code-block:: python

    table = viewer.add_spreadsheet({"A": ["X", "X", "Y"], "B": [1, 2, 3]})
    table.dtypes["A"] = "category"
    table.dtypes["B"] = "float"
    table.data

.. code-block::

       A    B
    0  X  1.0
    1  X  2.0
    2  Y  3.0

.. code-block:: python

    table.dtypes

.. code-block::

    ColumnDtypeInterface(
        'A': category,
        'B': float64
    )

Simply delete items if you want to reset the dtype setting.

.. code-block:: python

    del table.dtypes["A"]
