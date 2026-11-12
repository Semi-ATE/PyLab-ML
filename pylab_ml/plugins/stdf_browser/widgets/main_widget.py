# -*- coding: utf-8 -*-
#

"""
Stdf Main Widget.
"""
import os

# Third party imports
from qtpy.QtWidgets import QHBoxLayout

# Local imports
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import (
    PluginMainWidget, PluginMainWidgetMenus)
from pylab_ml.plugins.stdf_browser.widgets.test_results import Test_Results

# Localization
_ = get_translation("spyder")


# --- Constants
# ----------------------------------------------------------------------------
class StdfWidgetActions:
    """ Constants for actions defined in StdfWidget. """
    # Triggers
    Import = "import"
    Reload = "reload"
    Graph = "graph"
    Json = "json"

    # Toggles
    # ToggleAutoFitPlotting = "toggle_auto_fit_plotting_action"


class StdfWidgetMainToolbarSections:
    """ Constants for sections in the main toolbar of StdfWidget. """
    Edit = "edit_section"
    Move = "move_section"
    Zoom = "zoom_section"


class StdfWidgetToolbarItems:
    """ Constants for toolbar items in StdfWidget. """
    ZoomSpinBox = "zoom_spin"


# --- Widgets
# ----------------------------------------------------------------------------
class StdfWidget(PluginMainWidget):             # ShellConnectMainWidget ,PluginMainWidget
    """ Main widget for the STDF plugin. """

    SHOW_MESSAGE_WHEN_EMPTY = True
    IMAGE_WHEN_EMPTY = "plots"
    MESSAGE_WHEN_EMPTY = _("No STDF file loaded")
    DESCRIPTION_WHEN_EMPTY = _(
        "Use the import button in the toolbar to open a STDF file."
    )

    def __init__(self, name=None, plugin=None, parent=None):
        """ Initialize the main widget.

        Parameters
        ----------
            name: str
                The name of the widget.
            plugin: SpyderPluginV2
                The plugin instance.
            parent: QWidget
                The parent widget.
        """
        super().__init__(name, plugin, parent)

        # Widgets
        self.widget = Test_Results(parent=self)
        self.set_content_widget(self.widget)

        self.widget.sig_data_changed.connect(self._on_data_changed)

        self.show_empty_message()

        # Resize to a huge width to get the right size of the thumbnail
        # scrollbar at startup.
        # self.resize(50000, self.height())

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        """ Return the title of the widget. """
        return _("Stdf")

    def get_focus_widget(self):
        """ Return the widget to give focus to when this plugin's dockwidget is raised. """
        # widget = self.current_widget      # existiert nur in ShellConnectMainWidget!
        return self.widget

    def setup(self):
        """ Setup the main widget. This is called after the widget is created and before it is shown for the first time. """
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
            # register_shortcut=True,                # used in the plot-plugin from spyder, but in this plugin an exceptin occure :-()
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
            tip=_("Plot the selected MPR rows"),
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
        self.add_item_to_menu(import_data_action, menu=context_menu)


    def update_actions(self):
        """ Update the enabled/disabled state of actions based on the current context. """
        has_file = self._has_file()
        has_data = self._has_data()

        states = {
            StdfWidgetActions.Import: True,
            StdfWidgetActions.Reload: bool(self.widget.filename),   # only if the file known
            StdfWidgetActions.Graph: self.weidgt.has_mpr,           # only if the file load
            StdfWidgetActions.Json: has_data,                       # only if the file load
            }
        for name, enabled in states.items():
            try:
                action = self.get_action(name)
            except KeyError:
                continue
            action.setEnabled(enabled)
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

    def _has_data(self):
        return len(self.widget.mpr_table)>0 or len(self.widget.ptr_table)>0

    def on_close(self):
        """ Handle the widget being closed. """
        print("   StdfWidget.on_close")
        return super().on_close()

     def on_close(self):
        if self.widget.plot_window is not None:
            self.widget.plot_window.close()
        return super().on_close()

    # ---- Private API
    # ------------------------------------------------------------------------
    def _on_data_changed(self):
        """ Zwischen Leerbild und Inhalt umschalten. """
        if self.widget.has_data():
            self.show_content_widget()
        else:
            self.show_empty_message()
        self.update_actions()

    # ---- Public API:
    # ------------------------------------------------------------------------

    def import_data(self):
        """Import data."""
        print('StdfWidget.import_data')
        result_h5 = os.path.join(self.widget.path, "result_h5", "no_lot.h5")
        if os.path.isfile(result_h5):
            os.remove(result_h5)
        self.widget.open_files()
        # self.update_actions()

    def reload_data(self):
        """Reload data."""
        print('StdfWidget.reload_data')
        if self.widget.filename != "":
            self.widget.open_files(os.path.join(self.widget.path, self.widget.filename))
        else:
            self.import_data()
        self.update_actions()

    def set_filename(self, path, filename):
        """ Set the filename and path for the widget. """
        print(f"StdfWidget.set_filename({path}, {filename})")
        self.widget.path = path
        self.widget.filename = filename + ".stdf"
        self.update_actions()

    def clear(self):
        """ Daten verwerfen und wieder das Leerbild zeigen. """
        self.widget.clear_data()

    def graph_show(self):
        """Show graph."""
        self.widget.graph_show()

    def generate_graph_from_json(self):
        """Generate 'pdf' from the '.json' files."""
        self.widget.generate_graph_from_json()
