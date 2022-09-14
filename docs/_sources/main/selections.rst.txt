===============================
Table Selections and Highlights
===============================

.. contents:: Contents
    :local:
    :depth: 1

Data Type of Table Selections
=============================

You'll get table selections using :attr:`selections` property as a :class:`SelectionRanges`
object. For instance, you opened a sample data

.. code-block:: python

    viewer.open_sample("iris")

and selected cells that correspond to ``df.iloc[0:100, 0:1]`` and ``df.iloc[2:3, 2:3]``,
you'll get following selection ranges.

.. code-block:: python

    table.selections

.. code-block::

    SelectionRanges([0:100, 0:1], [2:3, 2:3])

A :class:`SelectionRanges` object is a ``list`` like object. Each selection is a
``tuple[slice, slice]`` object.

.. code-block:: python

    table.selections[0]

.. code-block::

    (slice(0, 100, None), slice(0, 1, None))

Thus, you can use them directly in ``iloc`` method of :class:`DataFrame`.

.. code-block:: python

    table.data.iloc[table.selections[0]]

More simply, you can use :attr:`values` attribute to get values of selected table.

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

To update selections, you can use ``list``-like methods:

.. code-block:: python

    table.selections.append((slice(0, 10, None), slice(0, 1, None)))
    table.selections.pop(0)

or directly set a list to :attr:`selections`.

.. code-block:: python

    table.selections = [(slice(0, 10, None), slice(0, 1, None))]


Catch Change in Table Selections
================================

You can bind a callback function that will get called on every selection change event.
The :attr:`events` attribute is a :class:`SignalGroup` object of `psygnal <https://github.com/tlambert03/psygnal>`_.
``table.events.selections.connect`` registers a callback function to table events.

.. code-block:: python

    @table.events.selections.connect
    def _on_change(sel):
        print(sel)

Set Highlights
==============

"Highlight" is another feature of a table. Similar to a selection, a highlight is also
represented as a tuple of slices. Highlightened cells in a table are always painted.

Differences between a selection and a highlight are:

- Highlights cannot be set as dynamically as selections. You have to convert selections
  into highlights from right-click context menu or programatically using attribute
  :attr:`highlights`.
- Highlights do not vanish with mouse or keyboard operations.
- Highlights do not emit signals.
