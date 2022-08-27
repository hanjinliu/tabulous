===============
Set Cell Colors
===============

The foreground color (text color) and the background color can be set for each column.
You have to provide a colormap (function that maps values to colors) to do this. A colormap
must return a RGBA array (0-255) or a standard color name.

.. code-block:: python

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
