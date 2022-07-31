==========
Quickstart
==========

.. contents:: Contents
    :local:
    :depth: 1

Open A Table Viewer
===================

The main window of ``tabulous`` is a ``TableViewer`` instance.

.. code-block:: python

    from tabulous import TableViewer

    viewer = TableViewer()

You can also read table data from files to create a viewer.

.. code-block:: python

    import tabulous as tb

    # Read a csv file and add it to the viewer, just like pd.read_csv
    viewer = tb.read_csv("path/to/data.csv")

    # Read a Excel file and add all the sheets to the viewer.
    viewer = tb.read_excel("path/to/data.xlsx")

In a proper environment, ``tabulous`` command should be available.

.. code-block:: bash

    $ tabulous


Handle Tables
=============

Basically, table data is handled based on ``pandas``.
A ``TableViewer`` instance has several methods that add ``DataFrame`` to the viewer.

``Table``
---------

A ``Table`` is the most simple interface with ``DataFrame``.

- It stores a copy of an input ``DataFrame`` as is.
- It is not editable by default.
- Table shape is fixed unless data is fully updated by ``table.data = new_data``.
- When edited, the input value will be checked for the column data type. Wrong input will be
  rejected.

A ``DataFrame`` (or other objects that can be converted into a ``DataFrame``) can be added to
the viewer using ``add_table`` method.

.. code-block:: python

    import pandas as pd

    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    table = viewer.add_table(df, name="table name")
    table

.. code-block::

    Table<'table name'>

.. note::

    The newly added table is stored in ``tables`` property of the viewer in a ``list`` like
    structure.

    .. code-block:: python

        viewer.tables[0]  # the 0-th table

You can rename a table by ``name`` property. Tab name is also renamed accordingly.

.. code-block:: python

    table.name = "new name"


You have to pass ``editable=True`` or set the ``editable`` property to make it editable on GUI.

.. code-block:: python

    # pass the option
    table = viewer.add_table(df, editable=True)
    # or set the property
    table.editable = True

Table data is available in ``data`` property. You can also update the table data by directly
setting the ``data`` property.

.. code-block:: python

    df = table.data  # get the table data as a DataFrame
    table.data = df2  # set a new table data

The selected range of data is available in ``selections`` property. You can also
programmatically set table selections via ``selections`` property. Since table selections are
multi-selection, this property takes a ``list`` of ``tuple`` of two ``slice`` s
(``list[tuple[slice, slice]]``). Each item of list is ready for slicing using ``iloc`` method
of ``DataFrame``.

.. code-block:: python

    # print all the selected data
    for sel in table.selections:
        print(table.data.iloc[sel])

    # set selections
    table.selections = [(2, 4), (slice(10, 20), slice(2, 4))]

``SpreadSheet``
---------------

A ``SpreadSheet`` behaves more like Excel or Google Spreadsheet.

- It stores a copy of an input ``DataFrame`` as "string" types.
- It is editable by default and the input value will not be checked.
- Shape of table is unlimited (as far as it is not too large).
- The data type is inferred by ``pd.read_csv`` when it is obtained by ``data`` property.

For instance, if you manually edited the cells

+---+---+---+
|   | A | B |
+---+---+---+
| 0 | 2 | t |
+---+---+---+
| 1 | 3 | u |
+---+---+---+

then you'll get following ``DataFrame``.

.. code-block::

       A  B
    0  2  t
    1  3  u

    # dtypes
    A     int64
    B    object

A spreadsheet can be added to the viewer by ``add_spreadsheet`` method.

.. code-block:: python

    import pandas as pd

    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    sheet = viewer.add_spreadsheet(df, name="sheet")
    sheet

.. code-block::

    SpreadSheet<'sheet'>

Since a ``SpreadSheet`` is easily editable, it is reasonable to add an empty spreadsheet to
the viewer.

.. code-block:: python

    sheet = viewer.add_spreadsheet()  # add an empty spreadsheet

Interface with Viewer Components
================================

Get tables
----------

All the table data is available in ``tables`` property. It is a ``list`` like
object with some extended methods.

.. code-block:: python

    viewer.tables[0]  # the 0-th table
    viewer.tables["table-name"]  # the table with name "table-name"
    viewer.get("table-name", None)  # the table with name "table-name" if exists
    del viewer.tables[0]  # delete the 0-th table
    viewer.tables.move(0, 2)  # move the 0-th table to the 2-th position

You can also get currently acitive (visible) table or its index with
``viewer.current_table`` or ``viewer.current_index``.

``TableList`` object.

Embedded Console
================

To programmatically analyze table data, you can just open the embedded
interpreter. It is dependent on `qtconsole <https://qtconsole.readthedocs.io/en/stable/>`_
package.

The console is not visible by default. You can show it by setting ``visible``
property of ``console`` interface to ``True``

.. code-block:: python

    viewer.conosole.visible = True

or push ``Ctrl+Shift+C`` shortcut.

Key combo
=========

``tabulous`` supports many keyboard shortcuts including key combo.

All the global key map is listed in a widget that will be shown when you press
``Ctrl+Shift+?``.
