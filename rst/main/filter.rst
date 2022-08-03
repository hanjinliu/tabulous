=============
Filter Tables
=============

You can apply a filter to a table without converting the internal data.

.. contents:: Contents
    :local:
    :depth: 1

Apply Filters Programmatically
==============================

You only have to set a function that maps a :class:`DataFrame` to a 1-D boolean array to
the property ``filter``. For instance, following code

.. code-block:: python

    table.filter = lambda df: df["label"] == "A"

is essentially equivalent to slicing a :class:`DataFrame` with ``df[df["label"] == "A"]``.

If the table is

+---+---+-------+
|   | A | label |
+---+---+-------+
| 0 | 2 |   A   |
+---+---+-------+
| 1 | 3 |   B   |
+---+---+-------+
| 2 | 6 |   B   |
+---+---+-------+
| 3 | 4 |   A   |
+---+---+-------+

then it looks like following after applying the filter.

+---+---+-------+
|   | A | label |
+---+---+-------+
| 0 | 2 |   A   |
+---+---+-------+
| 3 | 4 |   A   |
+---+---+-------+


Use Query-style Filtering
=========================

TODO
