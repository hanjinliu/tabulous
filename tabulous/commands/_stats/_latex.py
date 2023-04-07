from __future__ import annotations

from functools import lru_cache
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

# See https://stackoverflow.com/questions/32035251/displaying-latex-in-pyqt-pyside-qtablewidget
@lru_cache(maxsize=20)
def latex_to_pixmap(latex: str, fs: int, color: str = "#000000") -> QtGui.QPixmap:
    fig = Figure()
    fig.patch.set_facecolor("none")
    fig.set_canvas(FigureCanvasAgg(fig))
    renderer = fig.canvas.get_renderer()

    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.patch.set_facecolor("none")
    t = ax.text(0, 0, latex, ha="left", va="bottom", fontsize=fs, color=color)

    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)

    text_bbox = t.get_window_extent(renderer)

    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height

    fig.set_size_inches(tight_fwidth, tight_fheight)

    buf, size = fig.canvas.print_to_buffer()
    qimage = QtGui.QImage.rgbSwapped(
        QtGui.QImage(buf, size[0], size[1], QtGui.QImage.Format.Format_ARGB32)
    )
    qpixmap = QtGui.QPixmap(qimage)

    return qpixmap


class QLatexLabel(QtW.QLabel):
    def __init__(self, latex: str, parent=None):
        super().__init__(parent)
        self._color = QtGui.QColor("#000000")
        self._latex = latex
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setLatex(latex)

    def latex(self) -> str:
        return self._latex

    def setLatex(self, latex: str):
        self.setPixmap(
            latex_to_pixmap(latex, self.font().pointSize(), self._color.name())
        )
        self._latex = latex
        self.adjustSize()

    def textColor(self) -> QtGui.QColor:
        return self._color

    def setTextColor(self, color) -> None:
        self._color = QtGui.QColor(color)
        self.setLatex(self._latex)
