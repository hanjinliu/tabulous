from tabulous import TableViewer
from tabulous.types import TableInfo
from magicgui import magicgui
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

@magicgui
def plotter(info: TableInfo["x", "y"]):
    df, (x, y) = info
    sns.swarmplot(x=x, y=y, data=df)
    plt.show()

if __name__ == "__main__":
    viewer = TableViewer()
    df = pd.DataFrame(
        {"label": ["A", "B", "A", "B", "B", "A"],
         "value-0": [2, 4, 1, 5, 3, 1],
         "value-1": [0.1, 0.3, 0.2, 0.2, 0.3, 0.2],}
    )
    viewer.add_table(df, name="data")
    viewer.add_dock_widget(plotter)
    viewer.show()
