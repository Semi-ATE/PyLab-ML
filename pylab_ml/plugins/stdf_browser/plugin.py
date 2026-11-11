# -*- coding: utf-8 -*-
#
# Copyright © Semi-ATE  Contributors
# Licensed under the terms of the GNU GENERAL PUBLIC LICENSE V2
# (see pylab_ml/LICENSE for details)

"""
STDF browser Plugin.
"""
import os
import logging

# Spyder imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import on_plugin_available   # on_plugin_teardown
from spyder.api.translations import get_translation

# Semi-ATE imports
from ate_spyder.plugin import ATE
from ate_spyder_lab_control.plugin_control import LabControlPlugin

# Local imports
from pylab_ml.plugins.stdf_browser.widgets.main_widget import StdfWidget

# Localization
_ = get_translation("spyder")

#Logging
logger = logging.getLogger(__name__)


class StdfBrowser(SpyderDockablePlugin):
    """Stdf-Browser plugin."""

    NAME = "Stdf"
    REQUIRES = [ATE.NAME, LabControlPlugin.NAME]
    OPTIONAL = []
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    WIDGET_CLASS = StdfWidget    
    CONF_SECTION = NAME    

    # DISABLE_ACTIONS_WHEN_HIDDEN = False

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name() -> str:
        return _("Stdf")

    @staticmethod
    def get_description() -> str:
        return _("Display and explore STDF-Data.")

    @classmethod
    def get_icon(cls):
        return cls.create_icon("hist")

    def on_initialize(self):
        logger.debug("StdfBrowser:on_initialize")

    # ---- Private API
    # ------------------------------------------------------------------------

    @on_plugin_available(plugin=ATE.NAME)
    def on_ate_available(self):
        """ Connect to ATE plugin when it becomes available and set up the STDF widget with the project information from ATE. """
        ate: ATE = self.get_plugin(ATE.NAME)
        ate.sig_ate_project_loaded.connect(self._setup_stdf_widget)
        ate.sig_ate_progname.connect(self.runflow_changed)
        ate.sig_stop_debugging.connect(self.runflow_stop)
        self._testing = False
        
    @on_plugin_available(plugin=LabControlPlugin.NAME)
    def on_labcontrol_available(self):
        labcontrol: LabControlPlugin = self.get_plugin(LabControlPlugin.NAME)
        labcontrol._widget.change_status_display.connect(self.change_controlstatus)

    def _setup_stdf_widget(self):
        """ Set up the STDF widget with the project information from ATE when a new project is loaded. """
        widget: StdfWidget = self.get_widget()
        ate: ATE = self.get_plugin(ATE.NAME)
        project_info = ate.get_project_navigation()
        widget.widget.path = os.path.join(project_info.project_directory, "output")

    def runflow_changed(self, progname: str):
        """ Update the STDF widget with the new program name when the runflow changes in ATE. """
        widget: StdfWidget = self.get_widget()
        widget._filename = progname
        
    def runflow_stop(self):
        print('   StdfBrowser.runflow_stop()')
        
    def change_controlstatus(self, msg, extendmsg=""):
        if msg == "terminated" or (msg == "idle" and self._testing):
            widget: StdfWidget = self.get_widget()        
            widget.set_filename(widget.widget.path, widget._filename)
            widget.reload_data()
        elif msg== "idle":
            self._testing = True

        if msg == "terminated":
            self._testing = False


