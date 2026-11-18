# -*- coding: utf-8 -*-

"""
This script contains the 'showStdf' class which is used to convert the '.stdf' file into '.hdf5' file and
then preprocess the data to fill in the 'QTableWidget' in the PyQt window. It also contains the 'Test_Results' class
which is used to display the preprocessed data in the PyQt window and also to generate graphs from the data.
"""

# Standard library imports
import json
import sys
import os

# Third library imports
from qtpy import PYQT5
from qtpy.QtCore import Signal, Qt, QCoreApplication
from qtpy.QtWidgets import (QApplication, QWidget, QFileDialog, QMenu,
                            QTableWidgetItem, QVBoxLayout, QAbstractItemView)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)
from qtpy.uic import loadUi
from qtpy import QtWidgets, QtGui
from Metis.tools import STDFHelper
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# spyder library imports
from spyder.api.widgets.mixins import SpyderWidgetMixin

from pylab_ml.plugins.stdf_browser.widgets.showstdf import showStdf, str2float

__version__ = "0.0.6"


TaPtrItems = {
    "TestNo": 0,
    "Test Name": 1,
    "LSL": 2,
    "LTL": 3,
    "Results": 4,
    "empty1": 5,
    "IC 1": 6,
    "IC 2": 7,
    "IC 3": 8,
    "empty2": 9,
    "UTL": 10,
    "USL": 11,
    "Mean": 12,
    "Min": 13,
    "Max": 14,
    "RMS": 15,
    "Test Failed": 16,
    "ICFailed": 17,
}


TaMprItems = {
    "TestNo": 0,
    "Test": 1,
    "PART_INDEX": 2,
    "Result_Count": 3,
    "LSL": 4,
    "LTL": 5,
    "Results": 6,
    "UTL": 7,
    "USL": 8,
    "Mean": 9,
    "Min": 10,
    "Max": 11,
    "RMS": 12,
    "Test Failed": 13,
}

class PlotWindow(QWidget):
    """Eigenständiges, wiederverwendbares Fenster mit Matplotlib-Canvas."""

    sig_closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("STDF Plot")
        self.figure = Figure(figsize=(6.4, 4.8), dpi=100, tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.resize(800, 600)

    def new_axes(self):
        """Figur leeren und neue Achse zurückgeben."""
        self.figure.clear()
        return self.figure.add_subplot(111)

    def refresh(self):
        """Neu zeichnen und Fenster anzeigen (ohne der Tabelle den Fokus zu nehmen)."""
        self.canvas.draw_idle()
        if not self.isVisible():
            self.show()
        self.raise_()

    def closeEvent(self, event):
        self.sig_closed.emit()
        super().closeEvent(event)


class TableWidget(QTableWidgetItem):
    """Custom QTableWidgetItem for handling numeric comparisons."""
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except Exception:
            return QTableWidgetItem.__lt__(self, other)


class Test_Results(QWidget, SpyderWidgetMixin):
    """
    This class is used to display the preprocessed data in the PyQt window and also to generate graphs from the data.
    It inherits from QWidget and SpyderWidgetMixin to create a custom widget for displaying test results.
    """
    sig_data_changed = Signal()
    sig_mpr_selection_changed = Signal()


    # Anzahl der Zeilen (ab der 2.), die eine eigene y-Achse bekommen.
    # 1 -> nur die zweite Zeile, 2 -> zweite und dritte Zeile, ...
    OWN_Y_AXIS_ROWS = 3


    def __init__(self, parent=None, background_color=None):
        """
        Initializes the Test_Results class and loads the UI file developed in QtDesigner.
        It also sets up the necessary variables and connects the signals to the respective functions.

        Parameters
        ----------
            parent : QWidget, optional
                The parent widget of this Test_Results widget. If None, it will be a top-level window.
            background_color : str, optional
                The background color of the widget. If None, the default color will be used.
        """
        if PYQT5:
            super().__init__(parent=parent, class_parent=parent)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        # Loading 'ui' files developed in 'QtDesigner'
        loadUi(__file__.replace(".py", ".ui"), self)

        self.path = ""
        self._filename = ""
        self.lot = ""
        self.ptr_table = pd.DataFrame()
        self.mpr_table = pd.DataFrame()
        self.plot_window = None
        self._updating = False

        self.filename = ""
        self.adjustUI()
        self._plotted_mpr = []      # DataFrame-Indizes der MPR-Zeilen im Plot
        self._connect_signals()
        self.update_tabs()

    def _connect_signals(self):
        # currentCellChanged reagiert auf Maus UND Tastatur
        self.tableWidget_ptr.currentCellChanged.connect(self._on_ptr_cell_changed)
        self.tableWidget_ptr.cellClicked.connect(self._reshow_plot_window)

        # MPR: ganze Zeilen, Mehrfachauswahl (Strg/Shift), KEIN automatischer Plot
        self.tableWidget_mpr.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget_mpr.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tableWidget_mpr.selectionModel().selectionChanged.connect(
            self._on_mpr_selection_changed)
        self.tableWidget_mpr.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tableWidget_mpr.customContextMenuRequested.connect(
            self._show_mpr_context_menu)

        # Filter
        self.enter_filter_test_name_ptr.textChanged.connect(self.filter_test_name_ptr)
        self.enter_filter_test_name_mpr.textChanged.connect(self.filter_test_name_mpr)
        # Nach dem Filtern können ausgewählte Zeilen ausgeblendet sein -> Icon neu prüfen
        self.enter_filter_test_name_mpr.textChanged.connect(
            lambda _: self.sig_mpr_selection_changed.emit())

        self.tabWidget.currentChanged.connect(self._on_tab_changed)

    def adjustUI(self):
        """ This method is used to adjust the UI elements of the PyQt window, such as setting the column width of the 'QTableWidget' and hiding the progress bar and status labels."""
        self.set_column_width()
        self._arrange_columns()

        # header_item = self.tableWidget_mpr.horizontalHeaderItem(TaMprItems["Test"])
        # if header_item is not None:
        #     header_item.setText("Test Name")
        #     print("setText")
        self.progressBar.hide()
        self.lstatus.setText("")
        self.llotid.setText("")

    def clear_data(self):
        """ Geladene Daten verwerfen (-> Spyder zeigt das Leerbild). """
        self._plotted_mpr = []
        self.clear_tables()
        self.ptr_table = pd.DataFrame()
        self.mpr_table = pd.DataFrame()
        self.keyPressEvent(None)
        self.update_tabs()
        if self.plot_window is not None:
            self.plot_window.close()
        self.sig_data_changed.emit()

    def open_files(self, fname=""):
        """
        This method is used to open the '.stdf' file and load the data into the PyQt window.

        Parameters
        ----------
            fname : str, optional
                The path to the '.stdf' file. If not provided, a file dialog will be opened to select the file.

        Returns
        -------
            bool
                True if the file was successfully opened and data was loaded, False otherwise.
        """
        path = self.path or os.getcwd()
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(
                self, "Open STDF File", path, "stdf Files (*.stdf *.std)")
            if not fname:
                return False
        if not os.path.exists(fname):
            return False

        self.path, self.filename = os.path.split(fname)
        self.progressBar.show()
        QCoreApplication.processEvents()
        try:
            if not self.loaddata():
                return False
            self._plotted_mpr = []
            self._updating = True
            self.keyPressEvent(None)
            self._fill_tables()
            self.update_tabs()
        finally:
            self._updating = False
            self.progressBar.hide()

        self.sig_data_changed.emit()
        return True

    def clear_tables(self):
        """Beide Tabellen vollständig leeren."""
        for table in (self.tableWidget_ptr, self.tableWidget_mpr):
            table.clearSelection()
            table.clearContents()
            table.setRowCount(0)

    def _fill_tables(self):
        tables = [self.tableWidget_ptr, self.tableWidget_mpr]
        # Sortierung während des Füllens AUS, sonst springen Zeilen bei setItem()
        sorting = [(t, t.isSortingEnabled()) for t in tables]
        for t in tables:
            t.setSortingEnabled(False)

        self.clear_tables()
        self.fill_ptr_data()
        self.fill_mpr_data()
        self.set_column_width()
        if self.has_ptr():
            self.colour_pass_fail_ptr_data()
        if self.has_mpr():
            self.colour_pass_fail_mpr_data()

        for t, enabled in sorting:
            t.setSortingEnabled(enabled)

        # Evtl. eingegebene Filter erneut anwenden
        self.filter_test_name_ptr(self.enter_filter_test_name_ptr.text())
        self.filter_test_name_mpr(self.enter_filter_test_name_mpr.text())

    def fill_ptr_data(self):
        """
        This method is used to fill the 'PTR' data in the 'QTableWidget' in the PyQt window.
        It iterates through the columns of the 'ptr_table' DataFrame and sets the values in the corresponding cells of the 'QTableWidget'.
        It also updates the progress bar to indicate the progress of filling the data.
        """
        table = self.tableWidget_ptr
        columns = list(self.ptr_table.columns[0:5]) + list(self.ptr_table.columns[5:13])
        targets = list(range(0, 5)) + list(range(10, 18))   # siehe TaPtrItems
        table.setRowCount(len(self.ptr_table))

        for n, (column, col) in enumerate(zip(columns, targets), start=1):
            for row, val in enumerate(self.ptr_table[column].tolist()):
                item = TableWidget(str(val))
                if col == 0:
                    item.setData(Qt.UserRole, row)   # DataFrame-Position merken
                table.setItem(row, col, item)
            self.printProgressBar(n, len(columns))

    def fill_mpr_data(self):
        """
        This method is used to fill the 'MPR' data in the 'QTableWidget' in the PyQt window.
        It iterates through the columns of the 'mpr_table' DataFrame and sets the values in the corresponding cells of the 'QTableWidget'.
        It also updates the progress bar to indicate the progress of filling the data.
        """
        table = self.tableWidget_mpr
        if not self.has_mpr():
            table.setRowCount(0)
            return

        columns = list(self.mpr_table.columns[0:14])
        table.setRowCount(len(self.mpr_table))
        for col, column in enumerate(columns):
            for row, val in enumerate(self.mpr_table[column].tolist()):
                item = TableWidget(str(val))
                if col == 0:
                    item.setData(Qt.UserRole, row)
                table.setItem(row, col, item)
            self.printProgressBar(col + 1, len(columns))

    def has_data(self):
        return self.has_ptr() or self.has_mpr()

    def has_ptr(self):
        return isinstance(self.ptr_table, pd.DataFrame) and not self.ptr_table.empty

    def has_mpr(self):
        return (isinstance(self.mpr_table, pd.DataFrame)
                and "Results" in self.mpr_table.columns
                and not self.mpr_table.empty)

    # To load Pandas dataframes
    def loaddata(self):
        """
        This method is used to load the data from the '.hdf5' file into Pandas DataFrames.
        It uses the 'showStdf' class to read the data and preprocess it for further analysis.

        Returns
        -------
            bool
                True if the data was successfully loaded, False otherwise.
        """
        print(f"Test_Results.loaddata : {self.path, self.filename, self.lot}")
        self.hdf5_data = showStdf(self.path, self.filename, self.lot, "result_h5", update_Progress_bar=self.update_Progress_bar)
        if not self.hdf5_data.init():
            self.lfilename.setText(f".../{self.filename} is not a valid stdf file")
            return False
        self.table_data = self.hdf5_data.raw_hdf5_data()
        self.ptr_table = self.table_data[0]
        self.mpr_table = self.table_data[1]
        return True

    # To generate '.png' images from the '.json' file
    def generate_graph_from_json(self):
        """
        This method is used to generate graphs from the data stored in a '.json' file.
        It reads the JSON file, processes the data, and creates plots using Matplotlib.

        Returns
        -------
            bool
                True if the graphs were successfully generated, False otherwise.
        """
        try:
            # Load the '.json' file
            jname = QFileDialog().getOpenFileName(self, "Open File", os.getcwd(), "JSON files (*.json)")
            with open(jname[0], "r") as f:
                self.json_data = json.load(f)

            temp_folder = "STDF_Graph_Folder"
            self.graph_folder = os.path.join(self.path, temp_folder)

            # If directory doesn't exist, then create it
            if not os.path.exists(self.graph_folder):
                os.makedirs(self.graph_folder)
            try:
                for i in range(0, len(self.json_data)):
                    if "y" not in self.json_data[str(i)]:
                        temp_a = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ].tolist()
                        temp_b = self.mpr_table["MPR.LO_LIMIT"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][0]
                        temp_c = self.mpr_table["MPR.HI_LIMIT"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][0]
                        temp_d = self.mpr_table["Min_Value"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ]
                        temp_e = self.mpr_table["Max_Value"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ]
                        temp_f = self.mpr_table["Mean_Value"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ]
                        temp_g = self.mpr_table["Result_Count"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][0]
                        temp_h = str(self.mpr_table["Units"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][0])
                        plt.plot(temp_a[0], "bo", markersize=1)
                        plt.hlines(temp_b, 0, temp_g, color="r")
                        plt.hlines(temp_c, 0, temp_g, color="r")
                        plt.hlines(temp_d, 0, temp_g, color="m")
                        plt.hlines(temp_e, 0, temp_g, color="m")
                        plt.hlines(temp_f, 0, temp_g, color="y")
                        plt.title(self.json_data[str(i)]["title"])
                        plt.ylabel(temp_h)

                    if "y" in self.json_data[str(i)]:
                        temp_a = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ].tolist()
                        temp_b = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["y"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["y"][1]
                        ].tolist()
                        temp_c = (
                            self.json_data[str(i)]["x"][0]
                            + "["
                            + str(self.json_data[str(i)]["x"][1])
                            + "]"
                            + " vs "
                            + self.json_data[str(i)]["y"][0]
                            + "["
                            + str(self.json_data[str(i)]["y"][1])
                            + "]"
                        )
                        temp_d = str(self.mpr_table["Units"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][0])
                        temp_e = str(self.mpr_table["Units"][self.mpr_table["Test"] == self.json_data[str(i)]["y"][0]][0])
                        plt.plot(temp_a[0], temp_b[0], "bo", markersize=1)
                        plt.xlabel(temp_d)
                        plt.ylabel(temp_e)
                        plt.title(self.json_data[str(i)]["title"])
                        plt.legend([temp_c])

                    if "y1" in self.json_data[str(i)]:
                        temp_a = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ].tolist()
                        temp_b = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["y1"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["y1"][1]
                        ].tolist()
                        temp_c = (
                            self.json_data[str(i)]["x"][0]
                            + "["
                            + str(self.json_data[str(i)]["x"][1])
                            + "]"
                            + " vs "
                            + self.json_data[str(i)]["y"][0]
                            + "["
                            + str(self.json_data[str(i)]["y"][1])
                            + "]"
                        )
                        temp_d = (
                            self.json_data[str(i)]["x"][0]
                            + "["
                            + str(self.json_data[str(i)]["x"][1])
                            + "]"
                            + " vs "
                            + self.json_data[str(i)]["y1"][0]
                            + "["
                            + str(self.json_data[str(i)]["y1"][1])
                            + "]"
                        )
                        plt.plot(temp_a[0], temp_b[0], "go", markersize=1)
                        plt.legend([temp_c, temp_d])

                    if "y2" in self.json_data[str(i)]:
                        temp_a = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["x"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["x"][1]
                        ].tolist()
                        temp_b = self.mpr_table["Results"][self.mpr_table["Test"] == self.json_data[str(i)]["y2"][0]][
                            self.mpr_table["PART_INDEX"] == self.json_data[str(i)]["y2"][1]
                        ].tolist()
                        temp_c = (
                            self.json_data[str(i)]["x"][0]
                            + "["
                            + str(self.json_data[str(i)]["x"][1])
                            + "]"
                            + " vs "
                            + self.json_data[str(i)]["y"][0]
                            + "["
                            + str(self.json_data[str(i)]["y"][1])
                            + "]"
                        )
                        temp_d = (
                            self.json_data[str(i)]["x"][0]
                            + "["
                            + str(self.json_data[str(i)]["x"][1])
                            + "]"
                            + " vs "
                            + self.json_data[str(i)]["y1"][0]
                            + "["
                            + str(self.json_data[str(i)]["y1"][1])
                            + "]"
                        )
                        temp_e = (
                            self.json_data[str(i)]["x"][0]
                            + "["
                            + str(self.json_data[str(i)]["x"][1])
                            + "]"
                            + " vs "
                            + self.json_data[str(i)]["y2"][0]
                            + "["
                            + str(self.json_data[str(i)]["y2"][1])
                            + "]"
                        )
                        plt.plot(temp_a[0], temp_b[0], "ro", markersize=1)
                        plt.legend([temp_c, temp_d, temp_e])

                    # Filename is assigned as the 'title' key in the '.json' file
                    filename = self.json_data[str(i)]["title"] + ".png"
                    plt.savefig(os.path.join(self.graph_folder, filename))
                    self.printProgressBar(i, len(self.json_data) - 1, prefix="Graph Generation:", suffix="Complete", length=50)
                    plt.clf()
                self.generate_pdf()
            except Exception:
                print("There is no MPR data to plot the graph or the plots already exists ...")
        except Exception:
            print("Select the JSON file correctly ...")

    # Function to generate the '.pdf' files containing all the images
    def generate_pdf(self):
        """
        This method is used to generate a PDF file containing all the images in a folder.
        It reads all the images in the specified folder, converts them to RGB format, and saves them as a single PDF file.
        """

        # Empty list to append all the images in a folder
        image_pdf_list = []

        for i in os.listdir(self.graph_folder):
            global img_rgb
            image_file = os.path.join(self.graph_folder, i)

            # Open an Image
            img = Image.open(image_file)

            # Convert the Image to a 'RGB' format
            img_rgb = img.convert("RGB")
            image_pdf_list.append(img_rgb)

        # Remove the image at the last index of the folder
        image_pdf_list.pop(-1)

        # Create a PDF folder to store the '.pdf' file
        pdf_directory = "PDF/"
        pdf_path = os.path.join(self.graph_folder, pdf_directory)

        if not os.path.exists(pdf_path):
            os.makedirs(pdf_path)

        pdf_file = "STDF_Graph_" + self.lot + ".pdf"

        # Save the PDF file
        img_rgb.save(pdf_path + pdf_file, save_all=True, append_images=image_pdf_list)

    def filter_test_name_ptr(self, filter_test):
        """
        This method is used to filter the 'PTR' data in the 'QTableWidget' based on the test name.
        It hides the rows that do not match the specified filter.

        Parameters
        ----------
            filter_test : str
                The test name to filter the data by. If an empty string is provided, all rows will be shown.

        Returns
        -------
            None.
        """

        temp = []
        self.keyPressEvent(None)
        if filter_test == '':
            for i in range(self.tableWidget_ptr.rowCount()):
                self.tableWidget_ptr.setRowHidden(i, False)
        else:
            for i in range(self.tableWidget_ptr.rowCount()):
                item = self.tableWidget_ptr.item(i, 1)
                if item is None:
                    continue
                match = filter_test.lower() in item.text().lower()
                if match:
                    temp.append(i)
                self.tableWidget_ptr.setRowHidden(i, True)

            if temp == []:
                for i in range(self.tableWidget_ptr.rowCount()):
                    self.tableWidget_ptr.setRowHidden(i, True)

            for val in temp:
                self.tableWidget_ptr.setRowHidden(val, False)

    def filter_test_name_mpr(self, filter_test):
        """
        This method is used to filter the 'MPR' data in the 'QTableWidget' based on the test name.
        It hides the rows that do not match the specified filter.

        Parameters
        ----------
            filter_test : str
                The test name to filter the data by. If an empty string is provided, all rows will be shown.

        Returns
        -------
            None.
        """
        temp = []
        self.keyPressEvent(None)
        if filter_test == '':
            for i in range(self.tableWidget_mpr.rowCount()):
                self.tableWidget_mpr.setRowHidden(i, False)
        else:
            for i in range(self.tableWidget_mpr.rowCount()):
                item = self.tableWidget_mpr.item(i, 2)
                if item is None:
                    continue
                match = filter_test.lower() in item.text().lower()
                if match:
                    temp.append(i)
                self.tableWidget_mpr.setRowHidden(i, True)

            if temp == []:
                for i in range(self.tableWidget_mpr.rowCount()):
                    self.tableWidget_mpr.setRowHidden(i, True)

            for val in temp:
                self.tableWidget_mpr.setRowHidden(val, False)

    def load_IC_data(self):
        """
        This method is used to load the IC data into the 'QTableWidget' in the PyQt window.
        It retrieves the selected IC values from the input fields and updates the corresponding cells in the table.
        It also highlights the cells that are out of the specified limits.
        """
        try:
            selected_IC1 = int(self.ic_Number1.text()) - 1
        except Exception:
            selected_IC1 = 100000
        try:
            selected_IC2 = int(self.ic_Number2.text()) - 1
        except Exception:
            selected_IC2 = 100000
        try:
            selected_IC3 = int(self.ic_Number3.text()) - 1
        except Exception:
            selected_IC3 = 100000

        self.tableWidget_ptr.sortItems(0)

        for i in range(0, len(self.ptr_table)):
            ltl = str2float(self.ptr_table["LTL"][i])
            utl = str2float(self.ptr_table["UTL"][i])
            try:
                if len(self.ptr_table["Result_Append"][i]) > (selected_IC1):
                    val = self.ptr_table["Result_Append"][i][selected_IC1]
                    self.tableWidget_ptr.setItem(i, 6, QtWidgets.QTableWidgetItem(str(val)))
                    if ltl != utl and ((self.ptr_table["Result_Append"][i][selected_IC1] < ltl) or (
                            self.ptr_table["Result_Append"][i][selected_IC1] > utl)):
                        self.tableWidget_ptr.item(i, 6).setBackground(QtGui.QColor(255, 0, 0))
                else:
                    self.tableWidget_ptr.setItem(i, 6, QtWidgets.QTableWidgetItem("NA"))

                if len(self.ptr_table["Result_Append"][i]) > (selected_IC2):
                    val = self.ptr_table["Result_Append"][i][selected_IC2]
                    self.tableWidget_ptr.setItem(i, 7, QtWidgets.QTableWidgetItem(str(val)))
                    if ltl != utl and ((self.ptr_table["Result_Append"][i][selected_IC2] < ltl) or (
                            self.ptr_table["Result_Append"][i][selected_IC2] > utl)):
                        self.tableWidget_ptr.item(i, 7).setBackground(QtGui.QColor(255, 0, 0))
                else:
                    self.tableWidget_ptr.setItem(i, 7, QtWidgets.QTableWidgetItem("NA"))

                if len(self.ptr_table["Result_Append"][i]) > (selected_IC3):
                    val = self.ptr_table["Result_Append"][i][selected_IC3]
                    self.tableWidget_ptr.setItem(i, 8, QtWidgets.QTableWidgetItem(str(val)))
                    if ltl != utl and ((self.ptr_table["Result_Append"][i][selected_IC3] < ltl) or (
                            self.ptr_table["Result_Append"][i][selected_IC3] > utl)):
                        self.tableWidget_ptr.item(i, 8).setBackground(QtGui.QColor(255, 0, 0))
                else:
                    self.tableWidget_ptr.setItem(i, 8, QtWidgets.QTableWidgetItem("NA"))
            except Exception:
                pass

    # Assigning desiered column width to particular columns
    def set_column_width(self):
        """
        This method is used to set the column width of the 'QTableWidget' in the PyQt window.
        It assigns specific widths to each column based on the content and importance of the data.
        It also sets a minimum section size for the horizontal header to ensure that the columns are not too narrow.
        """
        self.tableWidget_ptr.horizontalHeader().setMinimumSectionSize(10)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["TestNo"], 50)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["Test Name"], 180)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["LSL"], 75)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["LTL"], 75)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["Results"], 150)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["IC 1"], 30)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["IC 2"], 30)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["IC 3"], 30)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["empty1"], 10)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["empty2"], 10)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["UTL"], 75)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["USL"], 75)
        self.tableWidget_ptr.setColumnWidth(TaPtrItems["Test Failed"], 80)
        for j in range(0, len(self.ptr_table)):
            self.tableWidget_ptr.setItem(j, TaPtrItems["empty1"], QtWidgets.QTableWidgetItem())
            self.tableWidget_ptr.item(j, TaPtrItems["empty1"]).setBackground(QtGui.QColor(240, 240, 240))
            self.tableWidget_ptr.setItem(j, TaPtrItems["empty2"], QtWidgets.QTableWidgetItem())
            self.tableWidget_ptr.item(j, TaPtrItems["empty2"]).setBackground(QtGui.QColor(240, 240, 240))

        self.tableWidget_mpr.setColumnWidth(6, 300)

    # To Colour values based on whether test has been passed (PTR Table)
    def colour_pass_fail_ptr_data(self):
        """
        This method is used to color the values in the 'PTR' table based on whether the test has been passed or failed.
        It iterates through the rows of the 'ptr_table' DataFrame and checks the values in the 'Test_Failed' column.
        If the value is '0', it means the test has passed, and the corresponding cells are colored green.
        If the value is not '0', it means the test has failed, and the corresponding cells are colored red.
        Additionally, if there are any IC values that are out of limits, they are colored yellow.
        """

        for j in range(0, len(self.ptr_table)):
            # If values in the 'Test_Failed' column is '0' then test Passed
            if self.ptr_table["Test_Failed"][j] == 0:

                # Green Colour if test is passed
                # self.tableWidget_ptr.item(j, TaPtrItems["Results"]).setForeground(QtGui.QColor(0, 255, 0))
                self.tableWidget_ptr.item(j, TaPtrItems["Test Failed"]).setForeground(QtGui.QColor(0, 255, 0))
                pass
            else:

                # Red Colour if test is failed
                self.tableWidget_ptr.item(j, TaPtrItems["Test Name"]).setForeground(QtGui.QColor(255, 0, 0))
                self.tableWidget_ptr.item(j, TaPtrItems["Results"]).setForeground(QtGui.QColor(255, 0, 0))
                self.tableWidget_ptr.item(j, TaPtrItems["Test Failed"]).setForeground(QtGui.QColor(255, 0, 0))

                # Yellow Colour in the IC# Failed
                self.tableWidget_ptr.item(j, TaPtrItems["ICFailed"]).setForeground(QtGui.QColor(255, 255, 0))

    # To Colour values based on whether test has been passed (MPR Table)
    def colour_pass_fail_mpr_data(self):
        """
        This method is used to color the values in the 'MPR' table based on whether the test has been passed or failed.
        It iterates through the rows of the 'mpr_table' DataFrame and checks the values in the 'Test_Failed' column.
        If the value is '0', it means the test has passed, and the corresponding cells are colored green.
        If the value is not '0', it means the test has failed, and the corresponding cells are colored red.
        """
        for j in range(0, len(self.mpr_table)):

            # If values in the 'Test_Failed' column is '0' then test Passed
            if self.mpr_table["Test_Failed"][j] == 0:

                # Green Colour if test is passed
                self.tableWidget_mpr.item(j, 6).setForeground(QtGui.QColor(0, 255, 0))
                self.tableWidget_mpr.item(j, 13).setForeground(QtGui.QColor(0, 255, 0))
            else:
                # Red Colour if test is failed
                self.tableWidget_mpr.item(j, TaMprItems["Test"]).setForeground(QtGui.QColor(255, 0, 0))
                self.tableWidget_mpr.item(j, TaMprItems["Results"]).setForeground(QtGui.QColor(255, 0, 0))
                self.tableWidget_mpr.item(j, TaMprItems["Test Failed"]).setForeground(QtGui.QColor(255, 0, 0))

    @property
    def filename(self):
        """ Get the current filename. """
        return self._filename

    @filename.setter
    def filename(self, name):
        status = ""
        self.llotid.setText("")
        if name == "" and self._filename == "":
            self.lfilename.setText("no file loaded")
            return
        elif name != "":
            self._filename = name
            self.lfilename.setText(f"{self.path}/{self._filename}")
        if not os.path.exists(f"{self.path}/{self._filename}"):
            status = "file not exist"
        else:
            self.lot = STDFHelper.get_lot_id(f"{self.path}/{self._filename}")
            self.llotid.setText(self.lot)
        self.lstatus.setText(status)

    # Fuction to get the status bar for uploading in QtWindow
    def printProgressBar(self, iteration, total, prefix="", suffix="", decimals=1, length=100, fill="█", printEnd="\r"):
        """
        Call in a loop to create terminal progress bar

        Parameters
        ----------
            iteration : int
                Current iteration (Int)
            total : int
                Total iterations (Int)
            prefix : str, optional
                Prefix string (Str)
            suffix : str, optional
                Suffix string (Str)
            decimals : int, optional
                Positive number of decimals in percent complete (Int)
            length : int, optional
                Character length of bar (Int)
            fill : str, optional
                Bar fill character (Str)
            printEnd : str, optional
                End character (e.g. "\r", "\r\n") (Str)

        Returns
        -------
            None.
        """
        # percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        # filledLength = int(length * iteration // total)
        # bar = fill * filledLength + "-" * (length - filledLength)
        self.update_Progress_bar(iteration, total)

    def update_tabs(self):
        """PTR-/MPR-Display the register only if the corresponding data is available"""
        tabs = [
            (self._tab_index_of(self.tableWidget_ptr), self.has_ptr()),
            (self._tab_index_of(self.tableWidget_mpr), self.has_mpr()),
        ]
        for index, visible in tabs:
            if index >= 0:
                self.tabWidget.setTabVisible(index, visible)

        # Falls das aktuelle Register ausgeblendet wurde -> auf sichtbares wechseln
        current = self.tabWidget.currentIndex()
        if current < 0 or not self.tabWidget.isTabVisible(current):
            for index, visible in tabs:
                if index >= 0 and visible:
                    self.tabWidget.setCurrentIndex(index)
                    break

    def update_Progress_bar(self, count, maxcount):
        """
        This method is used to update the progress bar in the PyQt window.
        It sets the range and value of the progress bar based on the current count and maximum count.
        It also processes any pending events to ensure that the progress bar is updated in real-time.

        Parameters
        ----------
            count : int
                The current count or progress value.
            maxcount : int
                The maximum count or total value for the progress bar.

        Returns
        -------
            None.
        """
        self.progressBar.setRange(1, maxcount)
        self.progressBar.setValue(count)
        QCoreApplication.processEvents()

    # Trigger Function to close the window
    def close_window(self):
        """ This method is used to close the PyQt window. It can be triggered by a button click or any other event that requires the window to be closed. """
        self.close()

    # ---- Hilfsfunktionen
    @staticmethod
    def _df_index(table, row):
        """DataFrame-Position zu einer (evtl. sortierten) Tabellenzeile."""
        item = table.item(row, 0)
        if item is None:
            return None
        idx = item.data(Qt.UserRole)
        return None if idx is None else int(idx)

    @staticmethod
    def _limit(text):
        try:
            return str2float(str(text))
        except (ValueError, IndexError):
            return None   # z.B. leere Grenze ("inf" wurde zu "")

    # ---- Register ein-/ausblenden
    def _tab_index_of(self, widget):
        """Index der Tab-Seite, die 'widget' enthält (-1 falls keine)."""
        for i in range(self.tabWidget.count()):
            page = self.tabWidget.widget(i)
            if page is widget or page.isAncestorOf(widget):
                return i
        return -1

    # ---- Spaltenreihenfolge (nur visuell, logische Indizes bleiben gleich)
    @staticmethod
    def _move_column_after(table, logical, after_logical):
        """Spalte 'logical' visuell direkt hinter 'after_logical' platzieren."""
        header = table.horizontalHeader()
        src = header.visualIndex(logical)
        dst = header.visualIndex(after_logical)
        if src < 0 or dst < 0:
            return
        if src > dst:
            dst += 1          # beim Verschieben nach links hinter das Ziel
        if src != dst:
            header.moveSection(src, dst)

    def _arrange_columns(self):
        # PTR: Test Name | Test Failed | IC Failed | LSL | ...
        self._move_column_after(self.tableWidget_ptr,
                                TaPtrItems["Test Failed"], TaPtrItems["Test Name"])
        self._move_column_after(self.tableWidget_ptr,
                                TaPtrItems["ICFailed"], TaPtrItems["Test Failed"])

        # MPR: Test | Test Name | Test Failed | Part INdex | Result_Count | ...
        self._move_column_after(self.tableWidget_mpr,
                                TaMprItems["Test"], TaMprItems["PART_INDEX"])
        self._move_column_after(self.tableWidget_mpr,
                                TaMprItems["Test Failed"], TaMprItems["PART_INDEX"])

        # Optional: Benutzer darf Spalten per Drag & Drop verschieben
        # self.tableWidget_ptr.horizontalHeader().setSectionsMovable(True)
        # self.tableWidget_mpr.horizontalHeader().setSectionsMovable(True)

    def _get_plot_window(self):
        if self.plot_window is None:
            self.plot_window = PlotWindow(self)
            self.plot_window.sig_closed.connect(self._on_plot_window_closed)
        return self.plot_window

    def _reshow_plot_window(self, row, col):
        if self.plot_window is not None and not self.plot_window.isVisible():
            self.plot_window.refresh()

    # ---- MPR-Auswahl
    def _on_tab_changed(self, index):
        self.keyPressEvent(None)
        self.sig_mpr_selection_changed.emit()     # Icon hängt auch vom Register ab

    def _on_mpr_selection_changed(self, selected=None, deselected=None):
        if self._updating:
            return
        n = len(self.selected_mpr_indices())
        self.lstatus.setText(f"{n} MPR line(s) selected" if n else "")
        self.sig_mpr_selection_changed.emit()

    def selected_mpr_indices(self):
        """DataFrame-Indizes aller ausgewählten, sichtbaren MPR-Zeilen
        (in der aktuell angezeigten Reihenfolge)."""
        if not self.has_mpr():
            return []
        table = self.tableWidget_mpr
        rows = sorted({i.row() for i in table.selectionModel().selectedIndexes()})
        result = []
        for row in rows:
            if table.isRowHidden(row):            # durch Filter ausgeblendet
                continue
            idx = self._df_index(table, row)
            if idx is not None:
                result.append(idx)
        return result

    def can_plot_mpr(self):
        """True, wenn das MPR-Register aktiv ist und Zeilen ausgewählt sind."""
        return (self.has_mpr()
                and self.tabWidget.currentIndex() == self._tab_index_of(self.tableWidget_mpr)
                and bool(self.selected_mpr_indices()))

    # ---- PTR
    def _on_ptr_cell_changed(self, row, col, prev_row, prev_col):
        if self._updating or row < 0 or row == prev_row:
            return
        self.plot_ptr_row(row)

    def plot_ptr_row(self, row):
        idx = self._df_index(self.tableWidget_ptr, row)
        if idx is None:
            return
        rec = self.ptr_table.iloc[idx]
        self.lstatus.setText(f"ptr line {row + 1} selected")

        data = np.asarray(rec["Result_Append"], dtype=float)
        ltl, utl = self._limit(rec["LTL"]), self._limit(rec["UTL"])

        self._plotted_mpr = []
        pw = self._get_plot_window()
        ax = pw.new_axes()
        if ltl != utl:                      # ltl == utl == 0 -> keine Grenzen
            for lim in (ltl, utl):
                if lim is not None:
                    ax.axhline(lim, color="r")
        ax.plot(data, "bo-", markeredgecolor="magenta", markersize=3)
        ax.set_title(f"{self.filename} \\ {self.lot}")
        ax.set_xlabel("Part Index")

        ylabel = str(rec["Test"])
        parts = str(rec["LTL"]).split()
        if len(parts) > 1:
            ylabel += f"\n({parts[1]})"
        elif rec.get("PTR.UNITS"):
            ylabel += f"\n({rec['PTR.UNITS']})"
        ax.set_ylabel(ylabel)
        pw.refresh()

    # ---- MPR
    def plot_mpr(self, indices):
        if not self.has_mpr() or not indices:
            return
        self._plotted_mpr = list(dict.fromkeys(indices))   # Duplikate entfernen
        self._redraw_mpr_plot()

    def add_to_mpr_plot(self, indices):
        """Zeilen zum bestehenden MPR-Plot hinzufügen."""
        if not self.has_mpr() or not indices:
            return
        if not self._plotted_mpr or self.plot_window is None \
                or not self.plot_window.isVisible():
            # Noch kein MPR-Plot vorhanden -> wie 'Plot'
            self.plot_mpr(indices)
            return
        self._plotted_mpr += [i for i in indices if i not in self._plotted_mpr]
        self._redraw_mpr_plot()

    def remove_from_mpr_plot(self, indices):
        """Zeilen aus dem bestehenden MPR-Plot entfernen."""
        if not self._plotted_mpr:
            return
        remaining = [i for i in self._plotted_mpr if i not in indices]
        if remaining == self._plotted_mpr:
            return                                  # nichts davon war im Plot
        if not remaining:
            # Letzte Kurve entfernt -> Fenster schließen
            # (closeEvent -> sig_closed -> _plotted_mpr wird geleert)
            if self.plot_window is not None:
                self.plot_window.close()
            self._plotted_mpr = []
            self.lstatus.setText("")
            return
        self._plotted_mpr = remaining
        self._redraw_mpr_plot()

    def _redraw_mpr_plot(self):
        pw = self._get_plot_window()
        ax = pw.new_axes()
        self._draw_mpr(ax, self._plotted_mpr)
        pw.refresh()
        self.lstatus.setText(f"{len(self._plotted_mpr)} MPR line(s) in plot")

    def _on_plot_window_closed(self):
        self._plotted_mpr = []

    def _create_y_axes(self, ax, count):
        """Liste von 'count' Achsen mit gemeinsamer x-Achse:
        [linke Achse, rechte Achse, weitere versetzte rechte Achsen ...]."""
        axes = [ax]
        for k in range(1, count):
            twin = ax.twinx()
            if k > 1:
                # weitere Achsen nach rechts versetzen, damit sie sich nicht überlagern
                twin.spines["right"].set_position(("axes", 1.0 + 0.15 * (k - 1)))
            axes.append(twin)
        return axes

    def _draw_mpr(self, ax, idx):
        t = self.mpr_table
        title = f"{self.filename} \\ {self.lot}"

        if len(idx) == 1:
            # Einzelzeile: Verlauf mit Grenzen, Min/Max und Mittelwert
            i = idx[0]
            count = t["Result_Count"][i]
            for lim in (t["MPR.LO_LIMIT"][i], t["MPR.HI_LIMIT"][i]):
                if np.isfinite(lim):
                    ax.hlines(lim, 0, count, color="r")
            ax.hlines([t["Min_Value"][i], t["Max_Value"][i]], 0, count, color="m")
            ax.hlines(t["Mean_Value"][i], 0, count, color="y")
            ax.plot(t["Results"][i], "bo-", markeredgecolor="magenta", markersize=1)
            ax.set_title(f"{title}\n{t['Test'][i]} [{t['PART_INDEX'][i]}]")
            ax.set_ylabel(f'{t["Test"][i]}\n({t["Units"][i]})')
            ax.set_xlabel("Result Index")
            ax.grid(True, alpha=0.3)
            return

        # Mehrere Zeilen: 1. Zeile links, 2. (ggf. weitere) mit eigener y-Achse
        colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        n_axes = min(len(idx), 1 + self.OWN_Y_AXIS_ROWS)
        axes = self._create_y_axes(ax, n_axes)

        handles = []
        left_rows = []                      # Zeilen auf der linken Achse
        for n, i in enumerate(idx):
            color = colors[n % len(colors)]
            target = axes[n] if n < n_axes else axes[0]
            if target is axes[0]:
                left_rows.append(i)
            line, = target.plot(t["Results"][i], "o-", color=color,
                                markersize=1, linewidth=0.8,
                                label=f'{t["Test"][i]} [{t["PART_INDEX"][i]}]')
            handles.append(line)

            # Eigene Achse in Kurvenfarbe beschriften
            if target is not axes[0]:
                target.set_ylabel(f'{t["Test"][i]}\n({t["Units"][i]})', color=color)
                target.tick_params(axis="y", colors=color)
                target.spines["right"].set_color(color)

        # Linke Achse beschriften
        if len(left_rows) == 1:
            i = left_rows[0]
            color = colors[0]
            ax.set_ylabel(f'{t["Test"][i]}\n({t["Units"][i]})', color=color)
            ax.tick_params(axis="y", colors=color)
            ax.spines["left"].set_color(color)
        else:
            units = list(dict.fromkeys(str(t["Units"][i]) for i in left_rows))
            ax.set_ylabel(" / ".join(units))

        ax.set_title(f"{title}\n{len(idx)} MPR rows")
        ax.set_xlabel("Result Index")
        ax.grid(True, alpha=0.3)

        # Gemeinsame Legende auf der obersten Achse (sonst von Kurven verdeckt)
        axes[-1].legend(handles=handles,
                        fontsize="small" if len(idx) <= 15 else "x-small",
                        ncol=1 if len(idx) <= 15 else 2)

    def graph_show(self):
        """This method is used to plot the graph based on the selected rows in the 'MPR' table.
        It checks the number of selected rows and plots the graph accordingly."""
        indices = self.selected_mpr_indices()
        if indices:
            self.plot_mpr(indices)

    def _show_mpr_context_menu(self, pos):
        """Kontextmenü nur bei Rechtsklick auf eine selektierte MPR-Zeile."""
        table = self.tableWidget_mpr
        index = table.indexAt(pos)
        if not index.isValid() or not self.has_mpr():
            return

        selected_rows = {i.row() for i in table.selectionModel().selectedIndexes()}
        if index.row() not in selected_rows:
            return

        indices = self.selected_mpr_indices()
        if not indices:
            return

        plot_visible = self.plot_window is not None and self.plot_window.isVisible()
        new = [i for i in indices if i not in self._plotted_mpr]
        in_plot = [i for i in indices if i in self._plotted_mpr] if plot_visible else []

        menu = QMenu(self)
        plot_action = menu.addAction("Plot selected rows")
        add_action = menu.addAction("Add")
        add_action.setEnabled(bool(new))
        remove_action = menu.addAction("Remove")
        remove_action.setEnabled(bool(in_plot))

        action = menu.exec_(table.viewport().mapToGlobal(pos))
        if action is plot_action:
            self.plot_mpr(indices)
        elif action is add_action:
            self.add_to_mpr_plot(indices)
        elif action is remove_action:
            self.remove_from_mpr_plot(indices)

    def keyPressEvent(self, event):
        """
        This method is triggered when a key is pressed.
        If the 'Esc' key is pressed, it resets the 'last_selected_row' variable and clears the 'clicked_index' list.
        It also updates the status label to indicate that no line is selected.
        If the 'Return' key is pressed, it calls the 'load_IC_data' method to load the IC data into the table.

        Parameters
        ----------
            event : QKeyEvent
                The key event that triggered this method.
        """
        if event is None or event.key() == Qt.Key_Escape:
            if event is not None:                  # nur echte Esc-Taste
                self.tableWidget_mpr.clearSelection()
            self.lstatus.setText("")
        elif event.key() == Qt.Key_Return:
            self.load_IC_data()

if __name__ == "__main__":
    from IPython import get_ipython

    get_ipython().run_line_magic('matplotlib', 'qt')            # or 'inline'
    app = QApplication(sys.argv)
    mainwindow = Test_Results()
    widget = QtWidgets.QStackedWidget()
    widget.addWidget(mainwindow)
    widget.setWindowTitle("Semi-ATE Test Results")
    widget.resize(1920, 960)
    mainwindow.open_files()
    widget.show()
    try:
        sys.exit(app.exec_())
    except Exception:
        print("File Closed ...")
