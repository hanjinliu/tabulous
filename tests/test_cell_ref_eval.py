from tabulous import TableViewer
import pandas as pd

def test_scalar():
    viewer = TableViewer(show=False)
    sheet = viewer.add_spreadsheet(pd.DataFrame({"a": [1, 3, 5]}))
    qtable = sheet.native._qtable_view
    editor = qtable._create_eval_editor("&=np.mean(df.iloc[0:3, 0])", (0, 1))
    assert qtable._focused_widget_ref is not None
    editor.eval_and_close()
    assert (0, 1) in qtable._ref_graphs.keys()
    assert qtable._focused_widget_ref is None
    assert sheet.data.iloc[0, 1] == 3.0

    # changing data triggers re-evaluation
    sheet.cell[0, 0] = 4
    assert sheet.data.iloc[0, 1] == 4.0
    sheet.cell[0, 0] = 7
    assert sheet.data.iloc[0, 1] == 5.0
