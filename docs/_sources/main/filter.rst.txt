=================
Filter Table Data
=================

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

.. |filter| image:: ../../tabulous/_qt/_icons/filter.svg
  :width: 20em

You can open a overlay dialog to filter the table data from the |filter| button in the toolbar,
push key combo ``Alt, A, 2``, or right click on the tab.

In this widget you have to specify a query-style expression to apply the filter. For details,
see `the API reference of pandas.eval <https://pandas.pydata.org/docs/reference/api/pandas.eval.html>`_.
The line edit for filter expression supports auto-completion (Tab) and history browsing
(↑, ↓).

.. image:: ../fig/filter.gif
