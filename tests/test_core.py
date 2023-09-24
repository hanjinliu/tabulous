import tabulous as tbl
import pandas as pd
from pathlib import Path
import pytest
from glob import glob
import runpy
import warnings

DATA_PATH = Path(__file__).parent / "data"

def test_view():
    df = pd.read_csv(DATA_PATH / "test.csv")
    tbl.view_table(df).close()
    tbl.view_spreadsheet(df).close()

def test_io():
    tbl.read_csv(DATA_PATH / "test.csv").close()

@pytest.mark.parametrize(
    "fname", [f for f in glob("examples/*.py") if "napari" not in f and "seaborn" not in f]
)
def test_examples(fname):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        runpy.run_path(fname)
