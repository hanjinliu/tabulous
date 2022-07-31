=================================
Use Non-main Window Table Viewers
=================================

If you plan to use a table viewer as a child of another ``QWidget``, you can use a non-main
window version.

.. code-block:: python

    from tabulous import TableViewerWidget
    from qtpy.QtWidgets import QWidget

    viewer = TableViewerWidget()
    assert isinstance(viewer.native, QWidget)

If you want to use a ``magicgui`` version of it, you can use the following code.

.. code-block:: python

    from tabulous import MagicTableViewer
    from magicgui.widgets import Container

    viewer = MagicTableViewer()
    container = Container()
    container.append(viewer)
