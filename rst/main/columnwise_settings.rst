====================
Column-wise Settings
====================

Tables are composed of several columns with different data types. There are some settings
that can be applied to each column individually, for better visualizing the data and safely
editing the data.

.. contents:: Contents
    :local:
    :depth: 2

Colormap
========

Use Colormap Functions
----------------------

The foreground color (text color) and the background color can be set for each column.
You have to provide a colormap (function that maps values to colors) to do this. A colormap
must return a RGBA array (0-255) or a standard color name.

.. code-block:: python

    viewer = TableViewer()
    viewer.open_sample("iris")

    # set a continuous colormap to the "sepal_length" column
    @table.foreground_colormap("sepal_length")
    def _(x: float):
        red = np.array([255, 0, 0, 255], dtype=np.uint8)
        blue = np.array([0, 0, 255, 255], dtype=np.uint8)
        return (x - lmin) / lrange * blue + (lmax - x) / lrange * red

.. code-block:: python

    # set a discrete colormap to the "sepal_width" column
    @table.background_colormap("sepal_width")
    def _(x: float):
        return "green" if x < 3.2 else "violet"

.. image:: ../fig/colormap.png

Use Dictionaries
----------------

For categorical data, you can also use dictionaries to set the colors.

.. code-block:: python

    cmap = {
        "setosa": "red",
        "versicolor": "green",
        "virginica": "blue",
    }
    table.foreground_colormap("species", cmap)  # set cmap

Set Colormaps in GUI
--------------------

Some basic colormaps are available in the right-click context menu of the columns,
such as ``Color > Set foreground colormap``.

Validator
=========

Simple data type conversion is sometimes not enough. To make editing data safer, you can
customize the validator for each column.

Set validator Functions
-----------------------

A validator function doesn't care about the returned value. It should raise an exception
if the input value is invalid.

.. code-block:: python

    viewer = TableViewer()
    viewer.add_table({"sample": [1, 2, 3], "volume": [0., 0., 0.]}, editable=True)

    @table.validator("volume")
    def _(x: float):
        if x < 0:
            raise ValueError("Volume must be positive.")

.. note::

    A :class:`Table` object converts the input value to the data type of the column.
    The validator function is called *after* the conversion.

.. note::

    Unlike other column setting, validators can NOT be set from GUI. This is because
    changing data validation rule might break the safety of the table data.

Text Formatter
==============

Text formatters are used to convert the values to strings without changing the data
itself. This is useful for displaying data in a more readable format.

.. note::

    Text formatters are called every time cells are painted. Formatters should not
    take too much time to run.

Set formatter function
----------------------

As usual in this chapter, you can use functions that convert a value into a string
as formatter function. The formatted strings are not necessary to satisfy the
column specific validation including data type conversion.

.. code-block:: python

    viewer = TableViewer()
    table = viewer.open_sample("iris")

    @table.text_formatter("sepal_length")
    def _(x: float):
        return f"{x:.2f} cm"

Set formatter string
--------------------

Instead of passing a function, you can also use a ready-to-be-formatted strings.

.. code-block:: python

    table.text_formatter("sepal_length", "{:.2f} cm")

Example above is identical to passing ``"{:.2f} cm".format``.

Set Formatter in GUI
--------------------

Some basic formatters are available in the right-click context menu of the columns,
such as ``Formatter > Set text formatter``. You'll see a preview of the column in
the dialog.

Spreadsheet Data Types
======================


.. In ``SpreadSheet``, data types are determined for each column based on its content.
.. However, you may think of .
