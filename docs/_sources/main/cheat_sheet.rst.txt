============================
Cheat Sheet for Napari Users
============================

.. contents:: Contents
    :local:
    :depth: 2

Open a Viewer
=============

Just open a viewer
------------------

.. code-block:: python

    # napari
    viewer = napari.Viewer()

    # tabulous
    viewer = tabulous.TableViewer()

Open and read data
------------------

.. code-block:: python

    # napari
    viewer = napari.view_image(image)

    # tabulous
    viewer = tabulous.view_table(df)


Layers
======

List of layers
--------------

.. code-block:: python

    # napari
    viewer.layers

    # tabulous
    viewer.tables

Add data
--------

.. code-block:: python

    # napari
    viewer.add_image(image, name="Image")

    # tabulous
    viewer.add_table(df, name="table")

Get and set data
----------------

.. code-block:: python

    # napari
    viewer.layers[0].data
    viewer.layers[0].data = image

    # tabulous
    viewer.tables[0].data
    viewer.tables[0].data = df

Dock widgets
============

Add a dock widget
-----------------

.. code-block:: python

    # napari
    viewer.window.add_dock_widget(widget)

    # tabulous
    viewer.add_dock_widget(widget)
