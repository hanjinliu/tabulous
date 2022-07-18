# tabulous

A table data viewer for Python.

```python
from tabulous import open_sample

viewer = open_sample("iris")
```

![](image/viewer_iris.png)

`tabulous` is highly inspired by [napari](https://github.com/napari/napari) in its design and API.

```python
df = pd.read_csv("data.csv")
viewer.add_table(df)  # add table data to viewer
viewer.tables  # table list
table = viewer.tables[1]  # get table
table.data  # get pd.DataFrame object (or other similar one)

@table.events.data.connect
def _on_data_change(info):
    """data-changed callback"""

@table.events.selections.connect
def _on_selection_change(selections):
    """selection-changed callback"""

```

### Supported table types

- `Table`: A dtype-tagged table view with fixed size.
- `SpreadSheet`: A string based table editor. Table is converted into `pd.DataFrame` object with proper dtype consistent with `pd.read_csv`.
- `GroupBy`: A table group that corresponds to the returned object of the `groupby` method of `pd.DataFrame`.
