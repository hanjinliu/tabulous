=================================
Use Non-main Window Table Viewers
=================================

Aiming at better extensibility, ``tabulous`` is designed to allow many different types of
integration to external packages.

.. contents:: Contents
    :local:
    :depth: 1

Use TableViewer in Your Qt Widget
=================================

If you plan to use a table viewer as a child of another ``QWidget``, you can use a non-main
window version of it. The ``native`` property returns the Qt backend widget.

.. code-block:: python

    from tabulous import TableViewerWidget
    from qtpy import QtWidgets as QtW

    class MyQWidget(QtW.QMainWindow):
        def __init__(self):
            super().__init__()
            self.table = TableViewerWidget()
            self.setCentralWidget(self.table)

.. note::

    A benefit of using ``tabulous`` is that a table widget usually takes too much space but this
    problem can be solve by popup view of tables in ``tabulous``. See :doc:`table_advanced` for
    more detail.

.. note::

    To avoid conflicting with the main widget, the non-main-window version of table viewer has
    some restriction. For instance, embedded console does not open with shortcut ``Ctrl+Shift+C``
    so you have to programmatically open it by ``viewer.console.visible = True``.


Use TableViewer with magicgui
=============================

If you want to use a `magicgui <https://github.com/napari/magicgui>`_ version of it, you can
use ``MagicTableViewer``. ``MagicTableViewer`` is a subclass of ``TableViewerWidget`` and
``magicgui.widgets.Widget`` so it is compatible with all the ``magicgui`` functionalities.

In following simple example you can load a table data from a file.

.. code-block:: python

    from tabulous import MagicTableViewer
    from magicgui.widgets import Container, FileEdit

    viewer = MagicTableViewer()
    file_edit = FileEdit()
    file_edit.changed.connect(viewer.open)

    container = Container()
    container.append(viewer)
    container.append(file_edit)

    container.show()

``MagicTableViewer`` can also easily be used with `magic-class <https://github.com/hanjinliu/magic-class>`_.
Following example does similar thing as the one above.

.. code-block:: python

    from tabulous import MagicTableViewer
    from pathlib import Path
    from magicclass import magicclass, field

    @magicclass
    class A:
        table_viewer = field(MagicTableViewer)

        def load_data(self, path: Path):
            self.table_viewer.open(path)

    ui = A()
    ui.show()

Use Tables in Your Widget
=========================

All the tables can also be used in other widgets. For instance, following example shows how to
use a spreadsheet in your widget.

.. code-block:: python

    from tabulous.widgets import SpreadSheet
    from qtpy.QtWidgets import QWidget, QVBoxLayout

    class MyWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.setLayout(QVBoxLayout())
            self.layout().addWidget(SpreadSheet().native)

    widget = MyWidget()
    widget.show()

Table-specific shortcuts, such as copy/paste and undo/redo are available in the table.
