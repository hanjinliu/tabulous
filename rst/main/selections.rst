================
Table Selections
================

.. contents:: Contents
    :local:
    :depth: 1

Data Type of Table Selections
=============================

You'll get table selections using :attr:`selections` property as a :class:`SelectionRanges`
object.

.. code-block:: python

    table.selections

.. code-block::

    SelectionRanges([0:100, 0:1], [2:3, 2:3])

A :class:`SelectionRanges` object is a ``list`` like object except for being immutable.
Each selection is a ``tuple[slice, slice]`` object.

.. code-block:: python

    table.selections[0]

.. code-block::

    (slice(0, 100, None), slice(0, 1, None))

Thus, you can use them directly in ``iloc`` method of :class:`DataFrame`.

.. code-block:: python

    table.data.iloc[table.selections[0]]

More simply, you can use :attr:`data` attribute to get values of selected table.

.. code-block:: python

    table.selections.values[0]

.. code-block::

        sepal_length
    0            5.1
    1            4.9
    2            4.7
    3            4.6
    4            5.0
    ..           ...
    95           5.7
    96           5.7
    97           6.2
    98           5.1
    99           5.7

    [100 rows x 1 columns]

Catch Change in Table Selections
================================

.. code-block::

    @table.events.selections.connect
    def _on_change(sel):
        print(sel)
