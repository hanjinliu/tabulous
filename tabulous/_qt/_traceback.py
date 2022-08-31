from __future__ import annotations
import sys
import re
from typing import Callable, Generator, TYPE_CHECKING

from qtpy import QtWidgets as QtW

if TYPE_CHECKING:
    pass

if sys.platform == "win32":
    _FONT = "Consolas"
elif sys.platform == "darwin":
    _FONT = "Menlo"
else:
    _FONT = "Monospace"


class QtTracebackDialog(QtW.QDialog):
    """A dialog box that shows Python traceback."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Traceback")
        layout = QtW.QVBoxLayout()
        self.setLayout(layout)

        # prepare text edit
        self._text = QtW.QTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setFontFamily(_FONT)
        self._text.setLineWrapMode(QtW.QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text)

        self.resize(600, 400)

    def setText(self, text: str):
        """Always set text as a HTML text."""
        self._text.setHtml(text)


class QtErrorMessageBox(QtW.QMessageBox):
    """An message box widget for displaying Python exception."""

    def __init__(self, title: str, text_or_exception: str | Exception, parent):
        if isinstance(text_or_exception, str):
            text = text_or_exception
            exc = None
        else:
            if len(text_or_exception.args) == 0:
                text = ""
            else:
                text = text_or_exception.args[0]
            exc = text_or_exception
        MBox = QtW.QMessageBox
        super().__init__(
            MBox.Icon.Critical,
            str(title),
            str(text)[:1000],
            MBox.StandardButton.Ok | MBox.StandardButton.Help,
            parent=parent,
        )

        self._exc = exc

        self.traceback_button = self.button(MBox.StandardButton.Help)
        self.traceback_button.setText("Show trackback")

    def exec_(self):
        returned = super().exec_()
        if returned == QtW.QMessageBox.StandardButton.Help:
            tb = self._get_traceback()
            dlg = QtTracebackDialog(self)
            dlg.setText(tb)
            dlg.exec_()
        return returned

    @classmethod
    def raise_(cls, e: Exception, parent=None):
        """Raise exception in the message box."""
        self = cls(type(e).__name__, e, parent)
        self.exec_()

    def _get_traceback(self):
        if self._exc is None:
            import traceback

            tb = traceback.format_exc()
            print(tb)
        else:
            tb = get_tb_formatter()(self._exc, as_html=True)
        return tb


# Following functions are mostly copied from napari (BSD 3-Clause).
# See https://github.com/napari/napari/blob/main/napari/utils/notifications.py


def get_tb_formatter() -> Callable[[Exception, bool, str], str]:
    """
    Return a formatter callable that uses IPython VerboseTB if available.
    Imports IPython lazily if available to take advantage of ultratb.VerboseTB.
    If unavailable, cgitb is used instead, but this function overrides a lot of
    the hardcoded citgb styles and adds error chaining (for exceptions that
    result from other exceptions).

    Returns
    -------
    callable
        A function that accepts a 3-tuple and a boolean ``(exc_info, as_html)``
        and returns a formatted traceback string. The ``exc_info`` tuple is of
        the ``(type, value, traceback)`` format returned by sys.exc_info().
        The ``as_html`` determines whether the traceback is formatted in html
        or plain text.
    """
    try:
        import IPython.core.ultratb

        def format_exc_info(exc: Exception, as_html: bool, color="Neutral") -> str:
            # avoids printing the array data
            # some discussion related to obtaining the current string function
            # can be found here, https://github.com/numpy/numpy/issues/11266
            info = (
                exc.__class__,
                exc,
                exc.__traceback__,
            )
            try:
                import numpy as np

                np.set_string_function(
                    lambda arr: f"{type(arr)} {arr.shape} {arr.dtype}"
                )
                np_imported = True
            except ImportError:
                np_imported = False

            vbtb = IPython.core.ultratb.VerboseTB(color_scheme=color)
            if as_html:
                ansi_string = vbtb.text(*info).replace(" ", "&nbsp;")
                html = "".join(ansi2html(ansi_string))
                html = html.replace("\n", "<br>")
                html = (
                    f"<span style='font-family: monaco,{_FONT},monospace;'>"
                    + html
                    + "</span>"
                )
                tb_text = html
            else:
                tb_text = vbtb.text(*info)

            # resets to default behavior
            if np_imported:
                np.set_string_function(None)
            return tb_text

    except ModuleNotFoundError:
        import cgitb
        import traceback

        # cgitb does not support error chaining...
        # see https://peps.python.org/pep-3134/#enhanced-reporting
        # this is a workaround
        def cgitb_chain(exc: Exception) -> Generator[str, None, None]:
            """Recurse through exception stack and chain cgitb_html calls."""
            if exc.__cause__:
                yield from cgitb_chain(exc.__cause__)
                yield (
                    '<br><br><font color="#51B432">The above exception was '
                    "the direct cause of the following exception:</font><br>"
                )
            elif exc.__context__:
                yield from cgitb_chain(exc.__context__)
                yield (
                    '<br><br><font color="#51B432">During handling of the '
                    "above exception, another exception occurred:</font><br>"
                )
            yield cgitb_html(exc)

        def cgitb_html(exc: Exception) -> str:
            """Format exception with cgitb.html."""
            info = (type(exc), exc, exc.__traceback__)
            return cgitb.html(info)

        def format_exc_info(exc: Exception, as_html: bool, color=None) -> str:
            info = (
                exc.__class__,
                exc,
                exc.__traceback__,
            )
            # avoids printing the array data
            try:
                import numpy as np

                np.set_string_function(
                    lambda arr: f"{type(arr)} {arr.shape} {arr.dtype}"
                )
                np_imported = True
            except ImportError:
                np_imported = False
            if as_html:
                html = "\n".join(cgitb_chain(info[1]))
                # cgitb has a lot of hardcoded colors that don't work for us
                # remove bgcolor, and let theme handle it
                html = re.sub('bgcolor="#.*"', "", html)
                # remove superfluous whitespace
                html = html.replace("<br>\n", "\n")
                # but retain it around the <small> bits
                html = re.sub(r"(<tr><td><small.*</tr>)", "<br>\\1<br>", html)
                # weird 2-part syntax is a workaround for hard-to-grep text.
                html = html.replace(
                    "<p>A problem occurred in a Python script.  "
                    "Here is the sequence of",
                    "",
                )
                html = html.replace(
                    "function calls leading up to the error, "
                    "in the order they occurred.</p>",
                    "<br>",
                )
                # remove hardcoded fonts
                html = html.replace("\n", "<br>")
                html = (
                    f"<span style='font-family: monaco,{_FONT},monospace;'>"
                    + html
                    + "</span>"
                )
                tb_text = html
            else:
                # if we don't need HTML, just use traceback
                tb_text = "".join(traceback.format_exception(*info))
            # resets to default behavior
            if np_imported:
                np.set_string_function(None)
            return tb_text

    return format_exc_info


ANSI_STYLES = {
    1: {"font_weight": "bold"},
    2: {"font_weight": "lighter"},
    3: {"font_weight": "italic"},
    4: {"text_decoration": "underline"},
    5: {"text_decoration": "blink"},
    6: {"text_decoration": "blink"},
    8: {"visibility": "hidden"},
    9: {"text_decoration": "line-through"},
    30: {"color": "black"},
    31: {"color": "red"},
    32: {"color": "green"},
    33: {"color": "yellow"},
    34: {"color": "blue"},
    35: {"color": "magenta"},
    36: {"color": "cyan"},
    37: {"color": "white"},
}


def ansi2html(
    ansi_string: str, styles: dict[int, dict[str, str]] = ANSI_STYLES
) -> Generator[str, None, None]:
    """
    Convert ansi string to colored HTML

    Parameters
    ----------
    ansi_string : str
        text with ANSI color codes.
    styles : dict, optional
        A mapping from ANSI codes to a dict of css kwargs:values,
        by default ANSI_STYLES

    Yields
    ------
    str
        HTML strings that can be joined to form the final html
    """
    previous_end = 0
    in_span = False
    ansi_codes = []
    ansi_finder = re.compile("\033\\[" "([\\d;]*)" "([a-zA-z])")
    for match in ansi_finder.finditer(ansi_string):
        yield ansi_string[previous_end : match.start()]
        previous_end = match.end()
        params, command = match.groups()

        if command not in "mM":
            continue

        try:
            params = [int(p) for p in params.split(";")]
        except ValueError:
            params = [0]

        for i, v in enumerate(params):
            if v == 0:
                params = params[i + 1 :]
                if in_span:
                    in_span = False
                    yield "</span>"
                ansi_codes = []
                if not params:
                    continue

        ansi_codes.extend(params)
        if in_span:
            yield "</span>"
            in_span = False

        if not ansi_codes:
            continue

        style = [
            "; ".join([f"{k}: {v}" for k, v in styles[k].items()]).strip()
            for k in ansi_codes
            if k in styles
        ]
        yield '<span style="%s">' % "; ".join(style)

        in_span = True

    yield ansi_string[previous_end:]
    if in_span:
        yield "</span>"
        in_span = False
