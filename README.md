[![Downloads](https://pepy.tech/badge/tabulous/month)](https://pepy.tech/project/tabulous)
[![PyPI version](https://badge.fury.io/py/tabulous.svg)](https://badge.fury.io/py/tabulous)

# tabulous

A table data viewer for Python. [&rarr;📖 Documentation](https://hanjinliu.github.io/tabulous/)

![](https://github.com/hanjinliu/tabulous/blob/main/image/viewer_iris.png)

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

### A Wide Variety of Tables are Supported

|**Table**|**SpreadSheet**|
|:-:|:-:|
|![](https://github.com/hanjinliu/tabulous/blob/main/image/tab_table.gif)|![](https://github.com/hanjinliu/tabulous/blob/main/image/tab_sheet.gif)|
|A dtype-tagged table view with fixed size, aimed at viewing and editing `pd.DataFrame`. This table is the most basic one.|A string based table editor. Table is converted into `pd.DataFrame` object with proper dtypes consistent with reading CSV file using `pd.read_csv`.|

|**GroupBy**|**TableDisplay**|
|:-:|:-:|
|![](https://github.com/hanjinliu/tabulous/blob/main/image/tab_groupby.gif)|![](https://github.com/hanjinliu/tabulous/blob/main/image/tab_display.gif)|
|A table group that corresponds to the returned object of the `groupby` method of `pd.DataFrame`.|A table viewer that hotly reloads data using provided loader function. Useful for streaming data from other softwares.|

### In-cell Evaluation

|**Simple Evaluation**|**Referenced Evaluation**|
|:-:|:-:|
|![](https://github.com/hanjinliu/tabulous/blob/main/image/eval.gif)|![](https://github.com/hanjinliu/tabulous/blob/main/image/ref_eval.gif)|
|Text starts with "=" is evaluated in-place.|Text starts with "&=" is evaluated with cell references and is updated every time table data is updated.|

### Rich Visualization

|**Cell colors**|**Highlighting**|
|:-:|:-:|
|![](https://github.com/hanjinliu/tabulous/blob/main/image/colormap.png)|![](https://github.com/hanjinliu/tabulous/blob/main/image/highlight.png)|
|Colormap defines text or background color based on the value.|Highlight is colored overlays.|

### Data Validation

|**Data type validation**|**Custom validation**|
|:-:|:-:|
|![](https://github.com/hanjinliu/tabulous/blob/main/image/validation.gif)|![](https://github.com/hanjinliu/tabulous/blob/main/image/validation_custom.gif)|
|Columns tagged with dtype will validate the input string and raise an error on entering invalid string.|You can also define custom validators for each column, such as confirming non-negative.|

### How it works.

```python
from tabulous import open_sample

viewer = open_sample("iris")  # open a sample data from seaborn

df = pd.read_csv("data.csv")
viewer.add_table(df)  # add table data to viewer
viewer.tables  # table list
table = viewer.tables[0]  # get table
table.data  # get pd.DataFrame object (or other similar one)

# Connect data changed signal
# See examples/03-0_data_changed_signal.py
@table.events.data.connect
def _on_data_change(info):
    """data-changed callback"""

# Connect selection changed signal
# See examples/03-1_selection_changed.py
@table.events.selections.connect
def _on_selection_change(selections):
    """selection-changed callback"""

```
