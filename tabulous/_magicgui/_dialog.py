from __future__ import annotations
from typing import Any, Callable, TypeVar
import warnings
import inspect

from qtpy import QtWidgets as QtW, QtGui
from magicgui import magicgui
from magicgui.widgets import Widget, Dialog
from tabulous.widgets import MagicTable
from tabulous.types import TableData

from ._register import find_table_viewer_ancestor

_F = TypeVar("_F", bound=Callable)


def dialog_factory(function: _F) -> _F:
    from magicgui.widgets import create_widget

    def _runner(parent=None, **param_options):
        # create a list of widgets, similar to magic_signature
        widgets: list[Widget] = []
        callbacks: dict[str, Callable[[Widget], Any]] = {}
        sig = inspect.signature(function)
        for name, param in sig.parameters.items():
            opt = param_options.get(name, {})
            opt.setdefault("gui_only", False)
            changed_cb = opt.pop("changed", None)
            if param.default is not inspect.Parameter.empty:
                opt.setdefault("value", param.default)
            if param.annotation is not inspect.Parameter.empty:
                opt.setdefault("annotation", param.annotation)
            opt.setdefault("name", name)
            kwargs: dict[str, Any] = {}
            for k in "value", "annotation", "name", "label", "widget_type", "gui_only":
                if k in opt:
                    kwargs[k] = opt.pop(k)
            widget = create_widget(**kwargs, options=opt)
            if changed_cb is not None:
                assert callable(changed_cb)
                callbacks[name] = changed_cb
            widgets.append(widget)

        dlg = Dialog(widgets=widgets)

        for name, cb in callbacks.items():
            dlg[name].changed.connect(lambda: cb(dlg))

        # if return annotation "TableData" is given, add a preview widget.
        if function.__annotations__.get("return") is TableData:
            table = MagicTable(
                data=[],
                name="preview",
                editable=False,
                tooltip="Preview of the result using the head of the input data.",
                gui_only=True,
            )
            table.zoom = 0.8
            dlg.append(table)

            @dlg.changed.connect
            def _on_value_change(*_):
                import pandas as pd

                kwargs = dlg.asdict()
                # Check the first data frame is not too large.
                argname, val = next(iter(kwargs.items()))
                if isinstance(val, pd.DataFrame):
                    num = 8400
                    if val.size > num:
                        kwargs[argname] = val.head(num // val.shape[1])
                try:
                    table.data = function(**kwargs)
                except Exception:
                    table.data = []

            dlg.changed.emit()

        dlg.native.setParent(parent, dlg.native.windowFlags())
        dlg._shortcut = QtW.QShortcut(QtGui.QKeySequence("Ctrl+W"), dlg.native)
        dlg._shortcut.activated.connect(dlg.close)
        dlg.reset_choices()
        if dlg.exec():
            out = function(**dlg.asdict())
        else:
            out = None
        return out

    return _runner


def dialog_factory_mpl(function: _F) -> _F:
    # NOTE: undefined type annotation and the "bind" argument is not stable in
    # magicgui. To avoid the error, we just remove the annotations.
    function.__annotations__.pop("ax", None)

    def _runner(parent=None, **param_options):
        dlg = magicgui(function, **param_options)

        from tabulous._qt._plot import QtMplPlotCanvas

        style = None
        bg = None
        if parent is not None:
            if viewer := find_table_viewer_ancestor(parent):
                if not viewer._qwidget._white_background:
                    style = "dark_background"
                bg = viewer._qwidget.backgroundColor().name()

        plt = QtMplPlotCanvas(style=style, pickable=False)
        if bg:
            plt.set_background_color(bg)
        dlg.native.layout().addWidget(plt)
        dlg.height = 400
        dlg.width = 280

        @dlg.changed.connect
        def _on_value_change(*_):
            kwargs = dlg.asdict()
            kwargs["ax"] = plt.ax
            if kwargs.get("ref", False):
                kwargs["ref"] = False
            try:
                plt.cla()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    function(**kwargs)
                plt.draw()
            except Exception:
                pass

        dlg.changed.emit()

        dlg.native.setParent(parent, dlg.native.windowFlags())
        dlg._shortcut = QtW.QShortcut(QtGui.QKeySequence("Ctrl+W"), dlg.native)
        dlg._shortcut.activated.connect(dlg.close)
        dlg.called.connect(lambda: dlg.close())
        return dlg.show()

    return _runner
