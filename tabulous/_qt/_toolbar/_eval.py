from __future__ import annotations

from . import _utils


class QLiteralEval(_utils.QCompletableLineEdit):
    def eval(self):
        """Evaluate the current text as a Python expression."""
        text = self.text()
        if text == "":
            return
        table = self.currentPyTable()
        df = table.data.eval(text, inplace=False)
        if "=" not in text:
            self._qtable_viewer._table_viewer.add_table(df, name=table.name)
        else:
            table.data = df  # TODO: this is massive. Should use assignColumn().
            table.move_iloc(None, -1)
        self.toHistory()

    def filter(self):
        """Update the filter of the current table using the expression."""
        text = self.text()
        if text == "":
            return
        table = self.currentPyTable()
        sl = table.data.eval(text, inplace=False)
        table.filter = sl
        self.toHistory()

    def query(self):
        """Add a filtrated data of the current table using the expression."""
        text = self.text()
        if text == "":
            return
        table = self.currentPyTable()
        sl = table.data.eval(text, inplace=False)
        self._qtable_viewer._table_viewer.add_table(table.data[sl], name=table.name)
        self.toHistory()

    def setMode(self, mode: str):
        try:
            self.enterClicked.disconnect()
        except TypeError:
            pass
        if mode == "eval":
            self.enterClicked.connect(self.eval)
        elif mode == "filter":
            self.enterClicked.connect(self.filter)
        elif mode == "query":
            self.enterClicked.connect(self.query)
        else:
            raise ValueError(mode)
