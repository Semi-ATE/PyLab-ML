# -*- coding: utf-8 -*-
#

"""
Stdf Main Widget.
"""

# Third party imports
from PyQt5 import QtWidgets, QtCore
from qtpy.QtWidgets import QHBoxLayout

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidgetMenus
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.utils.misc import getcwd_or_home
from spyder.utils.palette import QStylePalette
from stdf_browser.widgets.showstdf import Test_Results

# Localization
_ = get_translation("spyder")


MAIN_BG_COLOR = QStylePalette.COLOR_BACKGROUND_1


# --- Constants
# ----------------------------------------------------------------------------
class StdfWidgetActions:
    # Triggers
    Import = "import"
    Reload = "reload"
    Graph = "graph"
    Json = "json"

    # Toggles
    # ToggleAutoFitPlotting = "toggle_auto_fit_plotting_action"


class StdfWidgetMainToolbarSections:
    Edit = "edit_section"
    Move = "move_section"
    Zoom = "zoom_section"


class StdfWidgetToolbarItems:
    ZoomSpinBox = "zoom_spin"


# --- Widgets
# ----------------------------------------------------------------------------
class StdfWidget(PluginMainWidget):             # ShellConnectMainWidget ,PluginMainWidget

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)
        #QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)

        # Widgets
        self.widget = Test_Results(parent=self, background_color=MAIN_BG_COLOR)

        # Resize to a huge width to get the right size of the thumbnail
        # scrollbar at startup.
        self.resize(50000, self.height())

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _("Stdf")

    def get_focus_widget(self):
        widget = self.current_widget()

        return widget

    def setup(self):
        layout = QHBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)

        # Menu actions
        # self.fit_action = self.create_action(
        #     name=StdfWidgetActions.ToggleAutoFitPlotting,
        #     text=_("Fit plots to window"),
        #     tip=_("Automatically fit plots to Plot pane size."),
        #     toggled=True,
        #     initial=self.get_conf("auto_fit_plotting"),
        #     option="auto_fit_plotting",
        # )

        # Toolbar actions
        import_data_action = self.create_action(
            name=StdfWidgetActions.Import,
            text=_("Import data"),
            tip=_("Import data..."),
            icon=self.create_icon("fileimport"),
            triggered=self.import_data,
            # register_shortcut=True,                # uesed in the plot-plugin from spyder, but in this plugin an exceptin occure :-()
        )

        reload_data_action = self.create_action(
            name=StdfWidgetActions.Reload,
            text=_("Reload data"),
            tip=_("Reload data..."),
            icon=self.create_icon("restart"),
            triggered=self.reload_data,
        )

        graph_show_action = self.create_action(
            name=StdfWidgetActions.Graph,
            text=_("Show grap"),
            tip=_("Show grap..."),
            icon=self.create_icon("plot"),
            triggered=self.graph_show,
        )

        json_action = self.create_action(
            name=StdfWidgetActions.Json,
            text=_("Json"),
            tip=_("Generate 'pdf' from the '.json' files."),
            icon=self.create_icon("PDFIcon"),
            triggered=self.generate_graph_from_json,
        )

        # Options menu

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [
            import_data_action,
            reload_data_action,
            json_action,
            graph_show_action,
        ]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=StdfWidgetMainToolbarSections.Edit,
            )

        # Context menu
        context_menu = self.create_menu(PluginMainWidgetMenus.Context)
        for item in [import_data_action]:
            self.add_item_to_menu(item, menu=context_menu)

    def update_actions(self):
        value = False
#        widget = self.current_widget()

        for __, action in self.get_actions().items():
            try:
                if action and action not in [self.undock_action,
                                             self.close_action,
                                             self.dock_action,
                                             self.toggle_view_action,
                                             self.lock_unlock_action]:
                    action.setEnabled(value)

                    # IMPORTANT: Since we are defining the main actions in here
                    # and the context is WidgetWithChildrenShortcut we need to
                    # assign the same actions to the children widgets in order
                    # for shortcuts to work
                    # if figviewer:
                    #     figviewer_actions = figviewer.actions()
                    #     # thumbnails_sb_actions = thumbnails_sb.actions()

                    #     if action not in figviewer_actions:
                    #         figviewer.addAction(action)

                    # if action not in thumbnails_sb_actions:
                    #    thumbnails_sb.addAction(action)
            except (RuntimeError, AttributeError):
                pass

    def on_close(self):
        return super().on_close()

    # ---- Public API:
    # ------------------------------------------------------------------------

    def import_data(self):
        """Import data."""
        print('StdfWidget.import_data')
        self.widget.open_files()

    def reload_data(self):
        """Import data."""
        print('StdfWidget.reload_data')
        if self.widget.filename != "":
            self.widget.open_files(self.widget.path + "/" + self.widget.filename)
        else:
            self.import_data()

    def set_filename(self, path, filename):
        self.widget.path = path
        self.widget.filename = filename.lower() + ".stdf"

    def graph_show(self):
        """Import data."""
        self.widget.graph_show()

    def generate_graph_from_json(self):
        """Generate 'pdf' from the '.json' files."""
        self.widget.generate_graph_from_json()
