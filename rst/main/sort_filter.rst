======================
Sort/Filter Table Data
======================

Sorting and filtering is a common way to manage and inspect table data. These operations
are collectively called "proxy" because both of them intermediary map the original data to
new indices.

.. contents:: Contents
    :local:
    :depth: 1

Filtering
=========

Use filter functions
--------------------

You can set a function that maps a :class:`DataFrame` to a 1-D boolean array as a filter
function. This is a most straightforward way.

.. code-block:: python

    def filter_func(df):
        return df["label"] == "A"

    table.proxy.filter(filter_func)

    # or equivalently, use decorator
    @table.proxy.filter
    def filter_func(df):
        return df["label"] == "A"

This example is essentially equivalent to slicing a :class:`DataFrame` by ``df[df["label"] == "A"]``.

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

Use query-style expression
--------------------------

Instead of a function, you can also set a query-style expression as a filter.

.. code-block:: python

    table.proxy.filter("label == 'A'")

See `the API reference of pandas.eval <https://pandas.pydata.org/docs/reference/api/pandas.eval.html>`_
for details of the syntax.

Filter in GUI
-------------

.. |filter| image:: ../../tabulous/_qt/_icons/filter.svg
  :width: 20em

You can open a overlay dialog to filter the table data from the |filter| button in the toolbar,
push key combo starting with ``Alt``, or right click on the selected column(s).

The line edit for filter expression supports auto-completion (Tab) and history browsing
(↑, ↓).

.. image:: ../fig/filter.gif

Sorting
=======

Use sorting functions
---------------------

Similar to filtering, you can also set a function for sorting. In this case, the function
should map a :class:`DataFrame` to a 1-D interger array, just like :meth:`argsort`.

.. code-block:: python

    def sort_func(df):
        return df["x"].argsort()

    table.proxy.sort(sort_func)

    # or equivalently, use decorator
    @table.proxy.sort
    def sort_func(df):
        return df["x"].argsort()

If the table is

+---+---+----+
|   | x |  y |
+---+---+----+
| 0 | 2 | a0 |
+---+---+----+
| 1 | 3 | a1 |
+---+---+----+
| 2 | 1 | a2 |
+---+---+----+
| 3 | 0 | a3 |
+---+---+----+

then it looks like following after sorting.

+---+---+----+
|   | x |  y |
+---+---+----+
| 3 | 0 | a3 |
+---+---+----+
| 2 | 1 | a2 |
+---+---+----+
| 0 | 2 | a0 |
+---+---+----+
| 1 | 3 | a1 |
+---+---+----+

Sorting function doesn't always have to be surjective, i.e. it can return only a subset of
the source indices.

.. code-block:: python

    @table.proxy.sort
    def sort_func(df):
        # return the top 10 rows
        return df["x"].argsort()[:10]

Sort by a column
----------------

In most cases, you'd like to sort a table by a column, in ascending or descending order.
The :meth:`sort` method also supports this use case, by passing ``by`` argument.

.. code-block:: python

    table.proxy.sort(by="x")  # ascending order by default
    table.proxy.sort(by="x", ascending=False)  # descending order

Multi-column sorting is also supported.

.. code-block:: python

    table.proxy.sort(by=["x", "y"])

Sort in GUI
-----------

.. |sort| image:: ../../tabulous/_qt/_icons/sort_table.svg
  :width: 20em

You can sort selected column(s) by clicking |sort| button in the toolbar,
push key combo starting with ``Alt``, or right click on the selected column(s).
