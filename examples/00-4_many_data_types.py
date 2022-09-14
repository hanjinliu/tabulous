from tabulous import TableViewer
import pandas as pd

# You can check how data types are get edited by tabulous

if __name__ == "__main__":
    viewer = TableViewer()
    df = pd.DataFrame(
        data = {
            "integer": [1, 2, 3],
            "unsigned-integer": pd.Series([1, 2, 3], dtype="uint8"),
            "float": [1.1, 2.2, 3.3],
            "bool": [True, False, True],
            "category": pd.Series(["a", "b", "a"], dtype="category"),
            "datetime": pd.date_range("2020-01-01", periods=3),
            "timedelta": pd.timedelta_range("1 day", periods=3),
        }
    )

    table = viewer.add_table(df, editable=True)
    viewer.show()
