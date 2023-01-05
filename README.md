[![Python package index download statistics](https://img.shields.io/pypi/dm/tabulous.svg)](https://pypistats.org/packages/tabulous)
[![PyPI version](https://badge.fury.io/py/tabulous.svg)](https://badge.fury.io/py/tabulous)

# tabulous

A table data viewer for Python.

[&rarr;📖 Documentation](https://hanjinliu.github.io/tabulous/)

![](https://github.com/hanjinliu/tabulous/blob/main/image/viewer_example.png)

`tabulous` is highly inspired by [napari](https://github.com/napari/napari) in its design and API.

### Installation

###### Install all the dependencies including functionalities of loading sample data, plotting, etc.

```
pip install tabulous[all]
```

###### Install with PyQt backend.

```
pip install tabulous[pyqt5]  # Use PyQt5
pip install tabulous[pyqt6]  # Use PyQt6
```

## Examples of Supported Functionalities

#### Table sorting and table filtering

|**Sort**|**Filter**|
|:-:|:-:|
|![](https://github.com/hanjinliu/tabulous/blob/main/image/sort_example.png)|![](https://github.com/hanjinliu/tabulous/blob/main/image/filter_example.png)|

You can apply pre-defined or custom sorting/filtering functions to tables.
Data edition during sorting/filtering is also supported.

#### Command palette

![](https://github.com/hanjinliu/tabulous/blob/main/image/command_palette_example.png)

Couldn't find how to do it? Open the command palette and search for it!

#### Excel-like referenced in-cell evaluation

![](https://github.com/hanjinliu/tabulous/blob/main/image/eval_example.png)

Call `numpy` and `pandas` functions that you are familiar with directly in cells.

#### Rich visualization

![](https://github.com/hanjinliu/tabulous/blob/main/image/colormap_example.png)

Set colormaps that will help you.

#### Custom widget integration

![](https://github.com/hanjinliu/tabulous/blob/main/image/custom_widget_example.png)

Add your own `PyQt`/`magicgui` widgets to the application.
