=======================
Register Custom Actions
=======================

Tabulous viewer has several components that support custom action registration
to the context menu. Suppose you have a viewer and a table:

.. code-block:: python

    from tabulous import TableViewer
    viewer = TableViewer()
    table = viewer.add_table({"a": [0, 1, 2]})

you can register functions using following methods.

- :meth:`viewer.tables.register_action` ... register action to the tab bar.
- :meth:`table.index.register_action` ... register action to the vertical header.
- :meth:`table.columns.register_action` ... register action to the horizontal header.
- :meth:`table.cells.register_action` ... register action to the table cells.

Register actions to the tab bar
===============================

Action for :meth:`viewer.tables.register_action` must have signature ``(index: int)``.
``index`` is the index of the right-clicked tab.

.. code-block:: python

    # register function "func" as an action named "Print tab name"
    @viewer.tables.register_action("Print tab name")
    def func(index: int):
        print(viewer.tables[i].name)

If you want to register it at a submenu, use ``">"`` as the separator.

.. code-block:: python

    @viewer.tables.register_action("Custom menu > Print tab name")
    def func(index: int):
        print(viewer.tables[i].name)

Register actions to the headers
===============================

Other :meth:`register_action` method works similarly. In the case of headers,
the signature for the action is also ``(index: int)``. Here, ``index`` is
the index of the right-clicked position (ready for :meth:`iloc`).

.. code-block:: python

    @table.index.register_action("Print this row")
    def func(index: int):
        print(table.data.iloc[index, :])

    @table.columns.register_action("Print this column")
    def func(index: int):
        print(table.data.iloc[:, index])

Register actions to the cells
=============================

The :meth:`register_action` method for cells also work in a similar way, but has
signature ``(index: tuple[int, int])`` unlike others. Here, ``index`` is a
tuple of row index and column index (ready for :meth:`iloc`).

.. code-block:: python

    @table.cell.register_action("Print this value")
    def func(index: tuple[int, int]):
        print(table.data.iloc[index])
