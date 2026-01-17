from himena import StandardType, WidgetDataModel
from himena.types import WidgetConstructor
from himena.consts import MenuId
from himena.plugins import register_widget_class, register_function, validate_protocol
from himena.standards.model_meta import DataFrameMeta
from tabulous.widgets import SpreadSheet, TableViewerWidget


@register_widget_class(StandardType.DATAFRAME, priority=10)
class PluginSpreadSheet(SpreadSheet):
    __himena_widget_id__ = "tabulous:PluginSpreadSheet"
    __himena_display_name__ = "Tabulous Spreadsheet"

    def __init__(self):
        super().__init__({})

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        self.data = model.value
        if isinstance(meta := model.metadata, DataFrameMeta):
            sels = []
            for rsel, csel in meta.selections:
                sels.append((slice(rsel, rsel), slice(csel, csel)))
            self.selections.update(sels)
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.data,
            type=StandardType.DATAFRAME,
            metadata=DataFrameMeta(
                current_position=list(self.current_index),
                selections=[
                    ((rsel.start, rsel.stop), (csel.start, csel.stop))
                    for rsel, csel in self.selections
                ],
            ),
        )

    @validate_protocol
    def native_widget(self):
        return self.native


class PluginTableViewer(TableViewerWidget):
    __himena_widget_id__ = "tabulous:PluginTableViewer"
    __himena_display_name__ = "Tabulous Table Viewer"

    def __init__(self):
        super().__init__(show=False)
        self.toolbar.show()

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 480

    @validate_protocol
    def native_widget(self):
        return self.native


@register_function(
    menus=MenuId.FILE_NEW,
    title="New tabulous spreadsheet",
    command_id="tabulous:new-spreadsheet",
)
def new_tabulous_spreadsheet() -> WidgetDataModel:
    """Create a new tabulous spreadsheet"""
    return WidgetDataModel(
        value=None,
        type=StandardType.DATAFRAME,
        force_open_with="tabulous:PluginSpreadSheet",
    )


@register_function(
    menus=MenuId.FILE_NEW,
    title="New tabulous table viewer",
    command_id="tabulous:new-table-viewer",
)
def new_tabulous_table_viewer() -> WidgetConstructor:
    """Create a new tabulous table viewer"""
    return PluginTableViewer
