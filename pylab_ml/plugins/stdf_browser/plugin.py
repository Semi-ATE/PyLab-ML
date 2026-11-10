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


class StdfBrowser(SpyderDockablePlugin):        # ShellConnectMixin
    """Stdf-Browser plugin."""

    NAME = "Stdf"
    REQUIRES = [ATE.NAME, Plugins.Toolbar, LabControlPlugin.NAME]     #_setup_stdf_widget
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
        print("   StdfBrowser:on_initialize")
        # widget: StdfWidget = self.get_widget()
        # print("stdf-browser.on_initialize()")
        pass

#    def update_font(self):
#        print("stdf-browser.update_font()")
#        color_scheme = self.get_color_scheme()
#        font = self.get_font()
#        self.get_widget().update_font(font, color_scheme)   # necessary?

    # ---- Private API
    # ------------------------------------------------------------------------

    @on_plugin_available(plugin=ATE.NAME)
    def on_ate_available(self):
        """ Connect to ATE plugin when it becomes available and set up the STDF widget with the project information from ATE. """
        print("   StdfBrowser:on_ate_available() start")
        ate: ATE = self.get_plugin(ATE.NAME)
        ate.sig_ate_project_loaded.connect(self._setup_stdf_widget)
        ate.sig_ate_progname.connect(self.runflow_changed)
        ate.sig_stop_debugging.connect(self.runflow_stop)
        print("   StdfBrowser:on_ate_available() done") 
        
    @on_plugin_available(plugin=LabControlPlugin.NAME)
    def on_labcontrol_available(self):
        print("   StdfBrowser:on_labcontrol_available() do nothing")         

    def _setup_stdf_widget(self):
        """ Set up the STDF widget with the project information from ATE when a new project is loaded. """
        print("   StdfBrowser:_setup_stdf_widget start")
        widget: StdfWidget = self.get_widget()
        ate: ATE = self.get_plugin(ATE.NAME)
        project_info = ate.get_project_navigation()
        widget.widget.path = os.path.join(project_info.project_directory, "output")
        
        ateToolbar = self.find_ate_toolbar()
        self.ateToolbar = ateToolbar if ateToolbar is not None else None
        print("   StdfBrowser:_setup_stdf_widget done")

    def runflow_changed(self, progname: str):
        """ Update the STDF widget with the new program name when the runflow changes in ATE. """
        widget: StdfWidget = self.get_widget()
        print(f'   StdfBrowser.runflow_changed({progname})')
        print(f'              {widget.widget.path}')
        #path = f"{self.ateToolbar.project_info.project_directory}/src/{self.ateToolbar.project_info.active_hardware}/{self.ateToolbar.project_info.active_base}"
        #print(f'stdf-broser.externalcallback {path} {filename}')
        widget.set_filename(widget.widget.path, progname)
        
    def runflow_stop(self):
        print('   StdfBrowser.runflow_stop() but do nothing')

    def externalcallback(self, filename):
        """ Update the STDF widget with the new filename when the external signal is emitted from the ATE toolbar. """
        print(f'   StdfBrowser.externalcallback {filename}')        
        path = f"{self.ateToolbar.project_info.project_directory}/src/{self.ateToolbar.project_info.active_hardware}/{self.ateToolbar.project_info.active_base}"

        #self.get_widget().set_filename(path, filename)
        
    def find_ate_toolbar(self):
       toolbar  = self.get_plugin(Plugins.Toolbar)
       ateToolbar = None        
       for bar in toolbar.toolbarslist:
           print(f"        {bar.ID}")
           if bar.ID == "ATE Plugin toolbar":
               ateToolbar = bar 
               break
       if ateToolbar is not None and hasattr(ateToolbar, 'external_signal'):
           print("   StdfBrowser.on_toolbar_available: Connect to Plugins.Toolbar")
           ateToolbar.external_signal.connect(self.externalcallback)
       else:
           print(f"    StdfBrowser.on_toolbar_available: Couldn't connect to Plugins.Toolbar = {ateToolbar}")
       return ateToolbar

