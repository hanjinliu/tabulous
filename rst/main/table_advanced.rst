===================
Working with Tables
===================

.. contents:: Contents
    :local:
    :depth: 2

Side Area
=========

Every table has a side area that can be used to add table-specific widgets or show
table-specific information.

Custom widgets
--------------

Custom Qt widgets or ``magicgui`` widgets can be added to the side area using
:meth:`add_side_widget` method.

.. code-block:: python

    table = viewer.tables[0]
    table.add_side_widget(widget)
    # if you want to give a name to the widget
    table.add_side_widget(widget, name="widget name")

Examples
^^^^^^^^

.. code-block:: python

    from magicgui import magicgui

    @magicgui
    def func():
        print(table.data.mean())

    table.add_side_widget(func)

Undo Stack
----------

Undo/redo is implemented for each table. You can see the registered operations in a list
view in the side area. You can open it by pressing ``Ctrl+H``.


Overlay Widget
==============

Instead of the side area, you can also add widgets as an overlay over the table. An
overlay widget is similar to the overlay charts in Excel.

.. code-block:: python

    table = viewer.tables[0]
    table.add_overlay_widget(widget)
    # if you want to give a label to the widget
    table.add_overlay_widget(widget, label="my widget")
    # you can give the top-left coordinate of the widget
    table.add_overlay_widget(widget, topleft=(5, 5))

Field Attributes of Tables
==========================

There are several fields that can be used to interact with table state and data.
Operations via table fields are undoable.

``cell``
--------

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

    - ``Table`` data will be updated in this way but ``SpreadSheet`` will not since
      the returned data is a copy.
    - :attr:`loc` and :attr:`iloc` does not check data type.
    - Table will not be updated immediately.

The :attr:`cell` field has sub-fields.

Cell references
^^^^^^^^^^^^^^^

All the in-cell functions with cell references are accessible via :attr:`ref` sub-field.

.. code-block:: python

    table = viewer.add_spreadsheet(np.arange(10))
    table.cell[0, 1] = "&=np.mean(df.iloc[:, 0])"
    print(table.cell.ref[0, 1])  # get the slot function at (0, 1)
    print(table.cell.ref[1, 1])  # KeyError

Cell labels
^^^^^^^^^^^

table.cell.label

.. code-block:: python

    print(table.cell.label[0, 1])
    table.cell.label[0, 1] = "mean ="

``plt``
-------

Since plotting is a common use case for table data analysis, plot canvases are implemented
by default. The basic plot functions are available in :attr:`plt` field with the
similar API as ``matplotlib.pyplot`` module.

.. code-block:: python

    table = viewer.tables[0]
    table.plt.plot(x, y)
    table.plt.hist(x)
    table.plt.scatter(x, y)

.. note::

    You can also update plot canvas from the "Plot" tab of the toolbar.


``index`` / ``columns``
-----------------------

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

``proxy``
---------

Proxy includes sorting and filtering, that is, deciding which rows to be shown and
which not to be.

.. code-block:: python

    table.proxy.filter("label == 'A'")  # filter by 'label' column
    table.proxy.sort("value")  # sort by 'value' column
    table.reset()  # reset proxy

See :doc:`sort_filter` for more details.

``dtypes``
----------

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


Use View Modes
==============

Dual View
---------

In dual view mode, table is split into two part and each part can be scrolled
and zoomed independently. This mode is useful to inspect large data.

Dual view is enabled by setting ``table.view_mode = "horizontal"`` for horizontal
view, and ``table.view_mode = "vertical"`` for vertical one.

.. code-block:: python

    table = viewer.add_table(data)
    table.view_mode = "horizontal"

To reset dual view, set the property to ``"normal"``.

.. code-block:: python

    table.view_mode = "normal"

Dual view can also be turned on by key combo ``Ctrl+K, H`` (horizontal) or
``Ctrl+K, V`` (vertical). Reset it by key combo ``Ctrl+K, N``.

Popup View
----------

In popup view mode, a large popup window appears and the table data is shown
inside it. This mode is useful when you want to focus on seeing or editing one
table, or the table viewer widget is docked in other widget so it is very small.

Popup view is enabled by setting ``table.view_mode = "popup"`` and can be reset
similar to dual view by ``table.view_mode = "normal"``

.. code-block:: python

    table = viewer.add_table(data)
    table.view_mode = "popup"

Dual view can also be turned on by key combo ``Ctrl+K, P``.

Tile View
---------

Tile view is a mode that shows different tables in a same window, while the
structure of table list and tabs are not affected.

How tiling works
^^^^^^^^^^^^^^^^

For instance, if you tiled tables "A" and "B", they will appear in the same
window, but tabs named "A" and "B" still exist in the tab bar. ``viewer.tables[i]``
also returns the same table as before. When tab "A" or "B" is clicked, the tiled
table with "A" and "B" is shown as ``A|B``.

You can tile the current table and the table next to it by shortcut ``Ctrl+K, ^``.
You can also programmatically tile tables by calling ``viewer.tables.tile([0, 1, 2])``.

Untiling
^^^^^^^^

Untiling is also well-defined operation. Let's say tabs "A", "B" and "C" is tiled so
these tabs show tiled view ``A|B|C``. If you untiled "B", "A" and "C" are re-tiled
while "B" returns the original state. Therefore, tabs "A" and "C" shows ``A|C`` and
tab "B" shows ``B``.

You can untile the current table by shortcut ``Ctrl+K, \``.
You can also programmatically untile tables by calling ``viewer.tables.untile([0, 1, 2])``.
