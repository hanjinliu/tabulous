==================
Custom Dock widget
==================

.. contents:: Contents
    :local:
    :depth: 2

Add Dock Widget
===============

.. code-block:: python

    from qtpy.QtWidgets import QWidget

    class MyWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setObjectName("MyWidget")

    widget = MyWidget()
    viewer.add_dock_widget(widget)


Use Magicgui Widget
===================

Basics
------

.. code-block:: python

    from magicgui import magicgui

    @magicgui
    def f(tip: str):
        viewer.status = tip

    viewer.add_dock_widget(f)

Tabulous Types
--------------

.. note::

    In ``napari``, you can use such as ``ImageData`` as an alias for ``np.ndarray`` type,
    while inform ``@magicgui`` that the data you want is the array stored in an ``Image``
    layer, or returned array should be added as a new ``Image`` layer. ``tabulous`` uses
    the same strategy to recover a ``pd.DataFrame`` from the table list or send a new one
    to the viewer.


.. code-block:: python

    from tabulous.types import TableData

    @magicgui
    def f(table: TableData) -> TableData:
        return table.apply([np.mean, np.std])

    viewer.add_dock_widget(f)
