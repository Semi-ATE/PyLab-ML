# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
STDF browser Plugin.
"""

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import on_plugin_available
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.api.translations import get_translation
from stdf_browser.widgets.main_widget import StdfWidget
from ate_spyder.plugin import ATE

# Localization
_ = get_translation("spyder")


class StdfBrowser(SpyderDockablePlugin):        # ShellConnectMixin
    """
    Stdf-Browser plugin.
    """

    NAME = "Stdf"
    WIDGET_CLASS = StdfWidget
    CONF_SECTION = NAME
    REQUIRES = [ATE.NAME]               #_setup_stdf_widget
    OPTIONAL = [Plugins.Toolbar, "ate"]
    CONF_FILE = False
    TABIFY = [Plugins.VariableExplorer, Plugins.Help]
    # DISABLE_ACTIONS_WHEN_HIDDEN = False

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Stdf")

    def get_description(self):
        return _("Display and explore STDF-Data.")

    def get_icon(self):
        return self.create_icon("hist")

    def on_initialize(self):
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
        widget: StdfWidget = self.get_widget()
        ate: ATE = self.get_plugin(ATE.NAME)
        ate.sig_ate_project_loaded.connect(self._setup_stdf_widget)
        ate.sig_ate_progname.connect(self.runflow_changed)

    def _setup_stdf_widget(self):
        widget: StdfWidget = self.get_widget()
        ate: ATE = self.get_plugin(ATE.NAME)
        project_info = ate.get_project_navigation()
        #widget.setup_widget(project_info)

    # @on_plugin_available(plugin=Plugins.Toolbar)
    # def on_toolbar_available(self):
    #     toolbar = self.get_plugin(Plugins.Toolbar)
    #     # print(toolbar.get_application_toolbar("ate_toolbar"))   # get an exception, "ate_toolbar" not found! Available toolbars are: ['file_toolbar', 'run_toolbar', 'debug_toolbar', 'main_toolbar']
    #     for bar in toolbar.toolbarslist:
    #         ateToolbar = bar if bar.ID == "ate_toolbar" else None
    #     if ateToolbar is not None and hasattr(ateToolbar, 'external_signal'):
    #         print("stdf-broser.on_toolbar_available: Connect to Plugins.Toolbar")
    #         ateToolbar.external_signal.connect(self.externalcallback)
    #     else:
    #         print(f"stdf-broser.on_toolbar_available: Couldn't connect to Plugins.Toolbar = {ateToolbar}")
    #     self.ateToolbar = ateToolbar

    def runflow_changed(self, progname: str):
        widget: StdfWidget = self.get_widget()
        print('StdfBrowser.runflow_changed()')
        #path = f"{self.ateToolbar.project_info.project_directory}/src/{self.ateToolbar.project_info.active_hardware}/{self.ateToolbar.project_info.active_base}"
        #print(f'stdf-broser.externalcallback {path} {filename}')
        #widget.set_filename(path, filename)

    def externalcallback(self, filename):
        path = f"{self.ateToolbar.project_info.project_directory}/src/{self.ateToolbar.project_info.active_hardware}/{self.ateToolbar.project_info.active_base}"
        print(f'stdf-broser.externalcallback {path} {filename}')
        #self.get_widget().set_filename(path, filename)
