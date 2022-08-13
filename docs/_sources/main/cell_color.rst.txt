===============
Set Cell Colors
===============

The foreground color (text color) and the background color can be set for each column.
You have to provide a colormap (function that maps values to colors) to do this. A colormap
must return a RGBA array (0-255) or a standard color name.

.. code-block:: python

    # set a continuous colormap to the "sepal_length" column
    @table.foreground_colormap("sepal_length")
    def f(v):
        i = (v - 4) / 4
        return [255, 0, int(255 * i), 255]

.. code-block:: python

    # set a discrete colormap to the "sepal_width" column
    @table.background_colormap("sepal_width")
    def f(v):
        if v < 3.2:
            return "green"
        else:
            return "purple"

.. image:: ../fig/colormap.png
