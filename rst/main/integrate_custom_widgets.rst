========================
Integrate Custom Widgets
========================

.. contents:: Contents
    :local:
    :depth: 1

.. include:: ../font.rst

There are several places to integrate your custom widgets to :mod:`tabulous` viewer.

Dock Widget Area
================

Dock widget areas are located outside the central table stack area. Widgets docked in
this area are always visible in the same place no matter which table is activated.

Add Qt Widgets
--------------

.. code-block:: python

    from qtpy.QtWidgets import QWidget

    class MyWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("MyWidget")

    widget = MyWidget()
    viewer.add_dock_widget(widget)


Use Magicgui Widget
-------------------

Basic usage
^^^^^^^^^^^

.. code-block:: python

    from magicgui import magicgui

    @magicgui
    def f(tip: str):
        viewer.status = tip

    viewer.add_dock_widget(f)

:mod:`tabulous` type annotations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

    In :mod:`napari``, you can use such as :mod:`ImageData` as an alias for :class:`np.ndarray` type,
    while inform ``@magicgui`` that the data you want is the array stored in an :class:`Image`
    layer, or returned array should be added as a new :class:`Image` layer. :mod:`tabulous` uses
    the same strategy to recover a :class:`pd.DataFrame` from the table list or send a new one
    to the viewer.

:class:`TableData` type is an alias of :class:`pd.DataFrame`. Arguments annotated by this
type will be interpreted as a combobox of table data by :mod:`magicgui`.

.. code-block:: python

    from tabulous.types import TableData

    @magicgui
    def f(table: TableData, mean: bool, std: bool, max: bool, min: bool) -> TableData:
        funcs = []
        for checked, f in [(mean, np.mean), (std, np.std), (max, np.max), (min, np.min)]:
            if checked:
                funcs.append(f)
        return table.apply(funcs)

    viewer.add_dock_widget(f)

.. image:: ../fig/dock_with_table_data_annotation.png

Table Side Area
===============

Every table has a side area that can be used to add table-specific widgets or show
table-specific information.

Custom Qt widgets or :mod:`magicgui` widgets can be added to the side area using
:meth:`add_side_widget` method.

.. code-block:: python

    table = viewer.tables[0]
    table.add_side_widget(widget)
    # if you want to give a name to the widget
    table.add_side_widget(widget, name="widget name")

    # example
    from magicgui import magicgui

    @magicgui
    def func():
        print(table.data.mean())

    table.add_side_widget(func)

Built-in Widgets
----------------

There are built-in widgets that uses the table side area by default.

1. Undo stack widget

    Undo/redo is implemented for each table. You can see the registered operations in a list
    view in the side area. You can open it by pressing :kbd:`Ctrl+H`.

2. Plot canvas

    Interactive :mod:`matplotlib` canvas is available in the "Plot" tool or the :attr:`plt`
    field of table widgets.

Table Overlay Widget
====================

Instead of the side area, you can also add widgets as an overlay over the table. An
overlay widget is similar to the overlay charts in Excel.

.. code-block:: python

    table = viewer.tables[0]
    table.add_overlay_widget(widget)
    # if you want to give a label to the widget
    table.add_overlay_widget(widget, label="my widget")
    # you can give the top-left coordinate of the widget
    table.add_overlay_widget(widget, topleft=(5, 5))
