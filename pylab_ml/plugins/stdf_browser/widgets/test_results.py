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
                            QTableWidgetItem, QVBoxLayout)
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


class PlotWindow(QWidget):
    """Eigenständiges, wiederverwendbares Fenster mit Matplotlib-Canvas."""

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
        self.last_selected_row = -1
        self.clicked_index = []
        self.plot_window = None
        self._updating = False

        self.filename = ""
        self.adjustUI()
        self._connect_signals()

    def _connect_signals(self):
        # currentCellChanged reagiert auf Maus UND Tastatur
        self.tableWidget_ptr.currentCellChanged.connect(self._on_ptr_cell_changed)
        self.tableWidget_mpr.currentCellChanged.connect(self._on_mpr_cell_changed)
        # Klick auf bereits gewählte Zeile: geschlossenes Plotfenster wieder zeigen
        self.tableWidget_ptr.cellClicked.connect(self._reshow_plot_window)
        self.tableWidget_mpr.cellClicked.connect(self._reshow_plot_window)

        self.enter_filter_test_name_ptr.textChanged.connect(self.filter_test_name_ptr)
        self.enter_filter_test_name_mpr.textChanged.connect(self.filter_test_name_mpr)
        self.tabWidget.currentChanged.connect(lambda _: self.keyPressEvent(None))

    def adjustUI(self):
        """ This method is used to adjust the UI elements of the PyQt window, such as setting the column width of the 'QTableWidget' and hiding the progress bar and status labels."""
        self.set_column_width()
        self.progressBar.hide()
        self.lstatus.setText("")
        self.llotid.setText("")

    def clear_data(self):
        """ Geladene Daten verwerfen (-> Spyder zeigt das Leerbild). """
        self.clear_tables()
        self.ptr_table = pd.DataFrame()
        self.mpr_table = pd.DataFrame()
        self.keyPressEvent(None)
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
            self._updating = True
            self.keyPressEvent(None)
            self._fill_tables()
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
            table.setRowCount(1)
            table.setItem(0, 2, QTableWidgetItem("MPR data is empty"))
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
                self.tableWidget_mpr.item(j, 1).setForeground(QtGui.QColor(255, 0, 0))
                self.tableWidget_mpr.item(j, 6).setForeground(QtGui.QColor(255, 0, 0))
                self.tableWidget_mpr.item(j, 13).setForeground(QtGui.QColor(255, 0, 0))

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

    def _get_plot_window(self):
        if self.plot_window is None:
            self.plot_window = PlotWindow(self)
        return self.plot_window

    def _reshow_plot_window(self, row, col):
        if self.plot_window is not None and not self.plot_window.isVisible():
            self.plot_window.refresh()

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
    def _on_mpr_cell_changed(self, row, col, prev_row, prev_col):
        if self._updating or row < 0:
            return
        idx = self._df_index(self.tableWidget_mpr, row)
        if idx is None:
            return
        self.last_selected_row = idx        # DataFrame-Index, nicht sichtbare Zeile
        if row != prev_row:
            self.plot_mpr([idx])

    def plot_mpr(self, indices):
        if not self.has_mpr() or not indices:
            return
        pw = self._get_plot_window()
        ax = pw.new_axes()
        try:
            self._draw_mpr(ax, indices[:4])
        except ValueError:
            ax.clear()
            ax.set_title("Result Count must match ...")
        pw.refresh()

    def _draw_mpr(self, ax, idx):
        t = self.mpr_table
        title = f"{self.filename} \\ {self.lot}"

        if len(idx) == 1:
            i = idx[0]
            count = t["Result_Count"][i]
            for lim in (t["MPR.LO_LIMIT"][i], t["MPR.HI_LIMIT"][i]):
                if np.isfinite(lim):
                    ax.hlines(lim, 0, count, color="r")
            ax.hlines([t["Min_Value"][i], t["Max_Value"][i]], 0, count, color="m")
            ax.hlines(t["Mean_Value"][i], 0, count, color="y")
            ax.plot(t["Results"][i], "bo-", markeredgecolor="magenta", markersize=1)
            ax.set_title(title)
            ax.set_ylabel(f'{t["Test"][i]}\n({t["Units"][i]})')

        elif len(idx) == 2:
            for i, fmt in zip(idx, ("go-", "ro-")):
                ax.plot(t["Results"][i], fmt, markersize=0.3, alpha=0.5,
                        label=t["Test"][i])
            ax.set_title(title)
            ax.set_ylabel(t["Units"][idx[0]])
            ax.legend()

        else:   # 3 oder 4: erste Auswahl = x, weitere = y
            def lab(i):
                return f'{t["Units"][i]}[{t["PART_INDEX"][i]}]'
            x = t["Results"][idx[0]]
            for i, fmt in zip(idx[1:], ("go", "ro", "yo")):
                ax.plot(x, t["Results"][i], fmt, markersize=1, alpha=0.5,
                        label=f"{lab(idx[0])} vs {lab(i)}")
            ax.set_title(f'{title}\n{t["Test"][idx[0]]}')
            ax.set_xlabel(t["Units"][idx[0]])
            ax.set_ylabel("   /   ".join(str(t["Units"][i]) for i in idx[1:]))
            ax.legend()

    def graph_show(self):
        """This method is used to plot the graph based on the selected rows in the 'MPR' table.
        It checks the number of selected rows and plots the graph accordingly."""
        indices = list(self.clicked_index)
        if not indices and self.last_selected_row >= 0:
            indices = [self.last_selected_row]
        self.plot_mpr(indices)
        self.clicked_index.clear()
        self.lstatus.setText("")

    def contextMenuEvent(self, event):
        """
        This method is triggered when the user right-clicks on the 'MPR' table.
        It checks if any row is selected and opens a context menu with options to plot a graph or add a graph.

        Parameters
        ----------
            event : QContextMenuEvent
                The context menu event that triggered this method.
        """
        if not (self.tableWidget_mpr.isVisible() and self.has_mpr()):
            return
        if not self.tableWidget_mpr.selectionModel().selection().indexes():
            return
        menu = QMenu(self)
        plot_action = menu.addAction("Plot Graph") if self.clicked_index else None
        add_action = menu.addAction("Add Graph")
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action is None:                       # Menü abgebrochen
            return
        if action is plot_action:
            self.graph_show()
        elif (action is add_action and self.last_selected_row != -1
              and self.last_selected_row not in self.clicked_index):
            self.clicked_index.append(self.last_selected_row)
            self.lstatus.setText(
                f"line {[i + 1 for i in self.clicked_index]} selected")

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
        print("Esc")
        if event is None or event.key() == Qt.Key_Escape:
            self.last_selected_row = -1
            self.clicked_index.clear()
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
