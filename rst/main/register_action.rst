=======================
Register Custom Actions
=======================

Tabulous viewer has several components that support custom action registration.

.. contents:: Contents
    :local:
    :depth: 2

Custom Contextmenu Actions
==========================

Currently there are four components that support custom action registration.

1. Tab bar
2. Vertical header
3. Horizontal header
4. Table cells

Suppose you have a viewer and a table:

.. code-block:: python

    from tabulous import TableViewer
    viewer = TableViewer()
    table = viewer.add_table({"a": [0, 1, 2]})

you can register functions using following methods.

1. :meth:`viewer.tables.register` ... register action to the tab bar.
2. :meth:`table.index.register` ... register action to the vertical header.
3. :meth:`table.columns.register` ... register action to the horizontal header.
4. :meth:`table.cells.register` ... register action to the table cells.

Register actions to the tab bar
-------------------------------

Action for :meth:`viewer.tables.register` must have signature
``(viewer, index: int)``. ``viewer`` is the viewer object to which the action is
registered and ``index`` is the index of the right-clicked tab.

.. code-block:: python

    from tabulous import TableViewerBase

    # register function "func" as an action named "Print tab name"
    @viewer.tables.register("Print tab name")
    def func(viewer: TableViewerBase, index: int):
        print(viewer.tables[i].name)

If you want to register it at a submenu, use ``">"`` as the separator.

.. code-block:: python

    @viewer.tables.register("Custom menu > Print tab name")
    def func(viewer: TableViewerBase, index: int):
        print(viewer.tables[i].name)

Register actions to the headers
-------------------------------

Other :meth:`register` method works similarly. In the case of headers,
the signature for the action is ``(table, index: int)``. Here, ``table`` is the
table object to which action is registered and ``index`` is the index of the
right-clicked position (ready for :meth:`iloc`).

.. code-block:: python

    from tabulous.widgets import TableBase

    @table.index.register("Print this row")
    def func(table: TableBase, index: int):
        print(table.data.iloc[index, :])

    @table.columns.register("Print this column")
    def func(table: TableBase, index: int):
        print(table.data.iloc[:, index])

Register actions to the cells
-----------------------------

The :meth:`register` method for cells also work in a similar way, but has
signature ``(table, index: tuple[int, int])``. Here, ``table`` is the table object
to which action is registered ``index`` is a tuple of row index and column index
(ready for :meth:`iloc`).

.. code-block:: python

    @table.cell.register("Print this value")
    def func(table: TableBase, index: tuple[int, int]):
        print(table.data.iloc[index])

Custom Keybindings
==================

Both viewers and tables have :attr:`keymap` attribute for keymap registration.

.. code-block:: python

    from tabulous import TableViewer

    viewer = TableViewer()

    # register function "func" as an action for key "Ctrl+P"
    @viewer.keymap.register("Ctrl+U")
    def func(viewer: TableViewer):
        print("Ctrl+U is pressed")

    @viewer.keymap.register("Ctrl+K, Ctrl+U")
    def func(viewer: TableViewer):
        print("keycombo Ctrl+K -> Ctrl+U is pressed")
