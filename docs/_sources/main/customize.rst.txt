========================
Customize Viewer Actions
========================

:mod:`tabulous` settings and configuration are stored in the user directory.
Configuration files will be created automatically when the viewer is launched
for the first time.

You can check the location of the user directory by running the following
command.

.. code-block:: bash

    $ tabulous --user-dir

Edit config.toml
================

The "config.toml" file describes the basic settings of the viewer.

.. code-block:: toml

    [console_namespace]
    tabulous = ...  # default identifier of the tabulous module
    viewer = ...  # default identifier of the viewer instance
    pandas = ...  # default identifier of the pandas module
    numpy = ...  # default identifier of the numpy module
    load_startup_file = ...  # load IPython startup file or not

    [table]
    max_row_count = ...  # maximum number of rows allowed to be added
    max_column_count = ...  # maximum number of rows allowed to be added
    font = ...  # font family name
    font_size = ...   # font size in points
    row_size = ...  # row height in pixels
    column_size = ...  # column width in pixels

    [cell]
    eval_prefix = ...  # prefix of for in-cell evaluation
    ref_prefix = ...  # prefix of for in-cell evaluation with cell references

    [window]
    ask_on_close = ...  # ask before closing the window or not
    show_console = ...  # show console on startup or not

.. note::

    To reset the configuration file to the default, run the following command.

    .. code-block:: bash

        $ tabulous --init-config

Edit post_init.py
=================

.. versionadded:: 0.4.1

The "post_init.py" file is used to customize contextmenus, keybindings, namespaces
and commands of the viewer.

Two initializer objects are used to register variables and functions to the
application *before* it is actually launched.

.. code-block:: python

    # post_init.py
    from tabulous.post_init import get_initializers

    viewer, table = get_initializers()

Each initializer object has similar attributes as the :class:`TableViewer` and
:class:`Table` respectively.

1. Contextmenu registration
    See :doc:`register_action` for what viewer/table components support the
    registration.

    - :meth:`viewer.tables.register` ... register action to the tab bar.
    - :meth:`table.index.register` ... register action to the vertical header.
    - :meth:`table.columns.register` ... register action to the horizontal header.
    - :meth:`table.cell.register` ... register action to the table cells.
    - :meth:`viewer.command_palette.register` ... register command to the command palette.
    - :meth:`viewer.keymap.register` ... register keybinding to the viewer.
    - :meth:`table.keymap.register` ... register keybinding to a table.

2. Namespace update
    - :meth:`viewer.cell_namespace.update` ... update the namespace in cells.
    - :meth:`viewer.console.update` ... update the namespace of the console.

Register actions using :meth:`register` method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Contextmenu, keybindings and commands can be registered using the :meth:`register`
method are also available for initialization.

.. code-block:: python

    # post_init.py

    @viewer.keymap.register("Ctrl+U")
    def my_func(viewer):
        print("Ctrl+U clicked")

    @table.cell.register("Test > Print location")
    def my_func(table, index):
        row, column = index
        print("Cell location: {}, {}".format(row, column))

    @viewer.command_palette.register("Test: Print string")
    def my_func(viewer):
        print("Command palette clicked")

Update namespaces
^^^^^^^^^^^^^^^^^

:attr:`viewer.cell_namespace` and :attr:`viewer.console` supports :meth:`update` and
:meth:`add` methods to update the namespace.

.. code-block:: python

    # post_init.py

    # use `update` method to update the namespace in a dict-like manner
    viewer.cell_namespace.update({"my_var": 1})
    viewer.console.update(pi=3.14159265359)

    # use `add` decorator
    @viewer.cell_namespace.add
    def SUM(x):
        return np.sum(x)

    @viewer.console.add
    class MyClass:
        pass
