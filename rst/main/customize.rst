========================
Customize Viewer Actions
========================

.. versionadded:: 0.4.1

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

The "post_init.py" file is used to customize contextmenus, keybindings, namespaces
and commands of the viewer.

Initializers Objects
--------------------

Two initializer objects are used to register variables and functions to the
application *before* it is actually launched.

.. code-block:: python

    # post_init.py
    from tabulous.post_init import get_initializers

    viewer, table = get_initializers()

Each initializer object has similar attributes as the :class:`TableViewer`` and
:class:`Table` respectively, as described in :doc:`register_action`.

1. Register right-click contextmenu Actions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # post_init.py
    viewer.
