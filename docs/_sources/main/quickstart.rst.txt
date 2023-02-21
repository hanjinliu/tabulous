==========
Quickstart
==========

.. contents:: Contents
    :local:
    :depth: 1

.. include:: ../font.rst

Open A Table Viewer
===================

The main window of :mod:`tabulous` is a :class:`TableViewer` instance.

.. code-block:: python

    from tabulous import TableViewer

    viewer = TableViewer()

You can also read table data from files to create a viewer.

.. code-block:: python

    import tabulous as tbl

    # Read a csv file and add it to the viewer, just like pd.read_csv
    viewer = tbl.read_csv("path/to/data.csv")

    # Read a Excel file and add all the sheets to the viewer.
    viewer = tbl.read_excel("path/to/data.xlsx")

If virtual environment (such as ``conda``) is used, you can use :mod:`tabulous` command to launch
a viewer.

.. code-block:: bash

    $ tabulous  # just launch a viewer

    $ tabulous ./path/to/data.csv  # open a table file in the viewer

Open an Interpreter
===================

:mod:`tabulous` viewer has an embedded Python interpreter console. It is not visible by default
but you can show it in several ways.

.. |toggle_console| image:: ../../tabulous/_qt/_icons/toggle_console.svg
  :width: 20em

1. Set :attr:`visible` property of :attr:`console` interface to ``True``:
   ``>>> viewer.conosole.visible = True``
2. Activate keyboard shortcut :kbd:`Ctrl` :kbd:`Shift` :kbd:`C`.
3. Click the |toggle_console| tool button in the the toolbar.

In ``tabulous`` viewer there are additional keybindings.

- :kbd:`Ctrl` :kbd:`Shift` :kbd:`↑`: Set console floating.
- :kbd:`Ctrl` :kbd:`Shift` :kbd:`↓`: Dock console.

Use Tables
==========

In :mod:`tabulous`, table data is handled based on :mod:`pandas`.
A :class:`TableViewer` instance has several methods that add :class:`DataFrame` to the viewer.

1. :meth:`add_table` ... add a table data as a :class:`Table` object.
2. :meth:`add_spreadsheet` ... add a table data as a :class:`SpreadSheet` object.

Table
-----

A :class:`Table` is the most simple interface with :class:`DataFrame`.

- It stores a copy of an input :class:`DataFrame` as is.
- It is not editable by default.
- Table shape is fixed unless data is fully updated by ``table.data = new_data``.
- When edited, the input value will be checked for the column data type. Wrong input will be
  rejected.

A :class:`DataFrame` (or other objects that can be converted into a :class:`DataFrame`) can be added to
the viewer using :meth:`add_table` method.

.. code-block:: python

    import pandas as pd

    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    table = viewer.add_table(df, name="table name")
    table

.. code-block::

    Table<'table name'>

.. image:: ../fig/table.png

.. note::

    The newly added table is stored in :attr:`tables` property of the viewer in a :class:`list` like
    structure.

    .. code-block:: python

        viewer.tables[0]  # the 0-th table

You can rename a table by :attr:`name` property. Tab name is also renamed accordingly.

.. code-block:: python

    table.name = "new name"


You have to pass ``editable=True`` or set the :attr:`editable` property to make it editable on GUI.

.. code-block:: python

    # pass the option
    table = viewer.add_table(df, editable=True)
    # or set the property
    table.editable = True

Table data is available in :attr:`data` property. You can also update the table data by directly
setting the :attr:`data` property.

.. code-block:: python

    df = table.data  # get the table data as a DataFrame
    table.data = df2  # set a new table data

The selected range of data is available in :attr:`selections` property. You can also
programmatically set table selections via :attr:`selections` property. Since table selections are
multi-selection, this property takes a ``list`` of slicable objects.

.. code-block:: python

    # print all the selected data
    for sel in table.selections:
        print(table.data.iloc[sel])

    # set selections
    table.selections = [(2, 4), (slice(10, 20), slice(2, 4))]

See :doc:`selections` for more details.

SpreadSheet
-----------

A :class:`SpreadSheet` behaves more like Excel or Google Spreadsheet.

- It stores a copy of an input :class:`DataFrame` as "string" types.
- It is editable by default and the input value will not be checked.
- Shape of table is unlimited (as far as it is not too large).
- The data type is inferred by :meth:`pd.read_csv` when it is obtained by :attr:`data` property.

For instance, if you manually edited the cells

.. image:: ../fig/spreadsheet.png

then you'll get following :class:`DataFrame`.

.. code-block::

       A  B
    0  2  t
    1  3  u

    # dtypes
    A     int64
    B    object

Rows and columns can be inserted or removed in the right-click contextmenu.

A spreadsheet can be added to the viewer by :meth:`add_spreadsheet` method.

.. code-block:: python

    import pandas as pd

    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    sheet = viewer.add_spreadsheet(df, name="sheet")
    sheet

.. code-block::

    SpreadSheet<'sheet'>

Since a :class:`SpreadSheet` is easily editable, it is reasonable to add an empty spreadsheet to
the viewer.

.. code-block:: python

    sheet = viewer.add_spreadsheet()  # add an empty spreadsheet

For more details ...
--------------------

- :doc:`/main/table_fields`
- :doc:`/main/table_view_mode`

Table List
==========

All the table data is available in :attr:`tables` property. It is a ``list`` like
object with some extended methods.

.. code-block:: python

    viewer.tables[0]  # the 0-th table
    viewer.tables["table-name"]  # the table with name "table-name"
    viewer.get("table-name", None)  # the table with name "table-name" if exists
    del viewer.tables[0]  # delete the 0-th table
    viewer.tables.move(0, 2)  # move the 0-th table to the 2-th position

You can also get currently acitive (visible) table or its index with
:attr:`viewer.current_table` or :attr:`viewer.current_index`.


Key combo
=========

:mod:`tabulous` supports many keyboard shortcuts including key combo.

All the global key map is listed in a widget that will be shown when you press
:kbd:`Ctrl` :kbd:`K` ⇒ :kbd:`Shift` :kbd:`?` key combo.

:attr:`keymap` is the key map registry object of table viewers. You can use :meth:`register`
to register custom key combo.

.. code-block:: python

    # simple key binding
    @viewer.keymap.register("Ctrl+P")
    def function(viewer):
        """do something"""

    # key combo
    @viewer.keymap.register("Ctrl+K, Ctrl+Q")
    def function(viewer):
        """do something"""

    # overwrite an existing key combo
    @viewer.keymap.register("Ctrl+K, Ctrl+Q", overwrite=True)
    def function(viewer):
        """do something"""

Command palette
===============

.. versionadded:: 0.4.0

:kbd:`Ctrl` :kbd:`Shift` :kbd:`P` or :kbd:`F1` opens a command palette widget. You can search for a variety of
registered commands.

.. image:: ../fig/command_palette.png
