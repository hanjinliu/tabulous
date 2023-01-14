=======================
Register Custom Actions
=======================

Tabulous viewer has several components that support custom action registration using
method :meth:`register`. All the :meth:`register` methods will be used as following syntax.

.. code-block:: python

    # viewer specific actions
    @viewer.XXX.register("<Location description>")
    def func(viewer):
        ...

    # table specific actions
    @table.XXX.register("<Location description>")
    def func(table):
        ...

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

.. warning::

    :meth:`register_action` is deprecated version of :meth:`register` until 0.4.0.

Register actions to the tab bar
-------------------------------

Action for :meth:`viewer.tables.register` must have signature ``(viewer, index: int)``
or its shorter version such as ``(viewer)``. ``viewer`` is the viewer object to which
the action is registered and ``index`` is the index of the right-clicked tab.

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

Other :meth:`register` method works similarly. In the case of headers, the signature
for the action is ``(table, index: int)`` or its shorter version such as ``(table)``.
Here, ``table`` is the table object to which action is registered and ``index`` is
the index of the right-clicked position (ready for :attr:`iloc`).

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

The :meth:`register` method for cells also work in a similar way, but has signature
``(table, index: tuple[int, int])`` or its shorter version such as ``(table)``.
Here, ``table`` is the table object to which action is registered ``index`` is a
tuple of row index and column index (ready for :attr:`iloc`).

.. code-block:: python

    @table.cell.register("Print this value")
    def func(table: TableBase, index: tuple[int, int]):
        print(table.data.iloc[index])

Custom Command in Command Palette
=================================

:mod:`tabulous` provides a command palette for executing actions. You can register
your own actions to the command palette using :meth:`register` method.

.. code-block:: python

    from tabulous import TableViewer

    viewer = TableViewer()

    # will be register under "User defined" context
    @viewer.command_palette.register("Print all table names")
    def func(viewer: TableViewer):
        for table in viewer.tables:
            print(table.name)

    # will be register under "Table" context
    @viewer.command_palette.register("Table: Print current table name")
    def func(viewer: TableViewer):
        print(viewer.current_table.name)


Custom Keybindings
==================

Both viewers and tables have :attr:`keymap` attribute for keymap registration.

1. :meth:`viewer.keymap.register` ... register keybindings to the viewer.
2. :meth:`table.keymap.register` ... register keybindings to each table.

.. code-block:: python

    from tabulous import TableViewer

    viewer = TableViewer()

    # register function "func" as an action for key "Ctrl+U"
    @viewer.keymap.register("Ctrl+U")
    def func(viewer: TableViewer):
        print("Ctrl+U is pressed")

    # register function "func" as an action for key combo "Ctrl+K, Ctrl+U"
    @viewer.keymap.register("Ctrl+K, Ctrl+U")
    def func(viewer: TableViewer):
        print("keycombo Ctrl+K -> Ctrl+U is pressed")
