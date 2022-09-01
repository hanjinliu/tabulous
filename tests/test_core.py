import tabulous as tbl
import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data"

def test_view():
    df = pd.read_csv(DATA_PATH / "test.csv")
    tbl.view_table(df).close()
    tbl.view_spreadsheet(df).close()

def test_io():
    tbl.read_csv(DATA_PATH / "test.csv").close()
