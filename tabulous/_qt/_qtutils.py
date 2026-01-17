from qtpy import QtWidgets as QtW


def isdeleted(qwidget: QtW.QWidget) -> bool:
    """Check if a Qt widget has been deleted."""
    try:
        qwidget.objectName()
    except RuntimeError as e:
        if str(e).startswith("wrapped C++ object of type"):
            return True
        raise
    else:
        return False
