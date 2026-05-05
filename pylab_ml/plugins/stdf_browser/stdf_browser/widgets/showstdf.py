# -*- coding: utf-8 -*-

# Standard library imports
import json
import sys
import os
from pathlib import Path

# Third library imports
from qtpy import PYQT5
from qtpy.QtCore import Qt, QCoreApplication
from qtpy.QtWidgets import (QApplication, QWidget, QFileDialog, QMenu,
                            QTableWidgetItem)
from qtpy.uic import loadUi
from qtpy import QtWidgets, QtGui
from Metis.tools import stdf2ph5, STDFHelper
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# spyder library imports
from spyder.api.widgets.mixins import SpyderWidgetMixin

__author__ = "Hariharan Karthikeyan"
__credits__ = ["Hariharan Karthikeyan"]
__email__ = "Hariharan.Karthikeyan@tdk.com"
__version__ = "0.0.5"


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


def str2float(string):
    result = string.strip().split(" ")
    return float(result[0])


class showStdf:
    RESULTDIR = "result_h5"

    # Dictionary for the Suffix in the [LSL, LTL, UTL, USL] columns
    SI = {
        1.000000e24: "y",
        1.000000e21: "z",
        1.000000e18: "a",
        1.000000e15: "f",
        1.000000e12: "p",
        1.000000e09: "n",
        1.000000e06: "µ",
        1.000000e03: "m",
        1.000000e02: "c",
        1.000000e01: "d",
        1.000000e00: "",
        1.000000e-03: "k",
        1.000000e-06: "M",
        1.000000e-09: "G",
        1.000000e-12: "T",
        1.000000e-15: "P",
        1.000000e-18: "E",
        1.000000e-21: "Z",
        1.000000e-24: "Y",
    }

    def __init__(self, path, filename, lot, resultdir, update_Progress_bar=None):
        self.hdf5_file = f"{path}/{self.RESULTDIR}/{lot}.h5"
        self.filename = filename
        self.path = path
        self.resultdir = resultdir
        self.update_Progress_bar = update_Progress_bar

        if Path(self.hdf5_file).is_file() and os.path.getmtime(path + "/" + filename) > os.path.getmtime(self.hdf5_file):
            os.remove(self.hdf5_file)

    def init(self):
        if not Path(self.hdf5_file).is_file():
            stdf = stdf2ph5.SHP(False, update_progress=self.update_Progress_bar)
            if not STDFHelper.is_plain_stdf(f"{self.path}/{self.filename}"):
                return False
            stdf.import_stdf_into_hdf5(f"{self.path}/{self.filename}", f"{self.path}/{self.resultdir}", disable_progress=True)
        return True

    # Function to convert '.hd5' to Pandas dataframe
    def raw_hdf5_data(self):

        # PREPROCESSING "PTR" DATA
        ptr = pd.read_hdf(self.hdf5_file, f"/raw_stdf_data/{self.filename}/PTR", mode="a")

        # Renaming columns to simple names
        ptr.rename(columns={"PTR.TEST_NUM": "TestNo", "PTR.RESULT": "Result", "PTR.TEST_TXT": "Test"}, inplace=True)

        # Sorting the values according to 'TestNo' column
        ptr.sort_values(["TestNo", "PART_INDEX"], inplace=True)

        ptr["fmt"] = ptr["PTR.C_HLMFMT"].apply(lambda x: x.decode()[1:])
        fmt = "7.3f"

        # Assigning values 10 to the power of 'PTR.RES_SCAL' column
        ptr["mul"] = 10 ** ptr["PTR.RES_SCAL"].apply(lambda x: float(x))

        # Rounding off the decimal digits to 3 values for easy readability
        ptr2 = ptr.groupby("TestNo")["Result"].apply(list).reset_index(name="Result_Append")

        # Making separate dataframe to concatenate the results of various IC's
        # of a particular test to a single list
        ptr2.drop(columns=ptr2.columns[0], axis=1, inplace=True)

        # Deleting the duplicate rows in the 'TestNo' column
        ptr.drop_duplicates(subset=["TestNo"], inplace=True, ignore_index=True)

        # Combining 'Result_Append' column to the 'ptr' dataframe
        ptr = ptr.assign(Result_Append=ptr2)

        # Creating empty lists which will be used in the below operation
        mean_result_ptr = []
        min_result_ptr = []
        max_result_ptr = []
        root_mean_square_ptr = []
        test_failed_ptr = []
        failed_idx_ptr = []
        failed_IC_ptr = []

        # Assigning values from the 'SI' dictionary above to the 'ptr['mul']'
        ptr["SI"] = ptr["mul"].apply(lambda x: self.SI[x])

        ptr["LTL"] = (
            (ptr["PTR.LO_LIMIT"] * ptr["mul"]).apply(lambda x: f"{x:{fmt}} ") + ptr["SI"].apply(lambda x: x) + ptr["PTR.UNITS"].apply(lambda x: x.decode())
        )
        ptr["UTL"] = (
            (ptr["PTR.HI_LIMIT"] * ptr["mul"]).apply(lambda x: f"{x:{fmt}} ") + ptr["SI"].apply(lambda x: x) + ptr["PTR.UNITS"].apply(lambda x: x.decode())
        )
        ptr["Test"] = ptr["Test"].apply(lambda x: x.decode())
        ptr["LSL"] = (
            (ptr["PTR.LO_SPEC"] * ptr["mul"]).apply(lambda x: f"{x:{fmt}} ") + ptr["SI"].apply(lambda x: x) + ptr["PTR.UNITS"].apply(lambda x: x.decode())
        )
        ptr["USL"] = (
            (ptr["PTR.HI_SPEC"] * ptr["mul"]).apply(lambda x: f"{x:{fmt}} ") + ptr["SI"].apply(lambda x: x) + ptr["PTR.UNITS"].apply(lambda x: x.decode())
        )

        ptr["LSL"] = ptr["LSL"].apply(lambda x: x if x.find("inf") < 0 else "")
        ptr["LTL"] = ptr["LTL"].apply(lambda x: x if x.find("inf") < 0 else "")
        ptr["UTL"] = ptr["UTL"].apply(lambda x: x if x.find("inf") < 0 else "")
        ptr["USL"] = ptr["USL"].apply(lambda x: x if x.find("inf") < 0 else "")
        ptr["PTR.UNITS"] = ptr["PTR.UNITS"].apply(lambda x: x.decode())

        # Storing 'Mean', 'Maximum', 'Minimum' and 'Root Mean Square' value of
        # test results of a test in 'max_result' variable
        for i in range(0, len(ptr)):
            result = ptr["Result_Append"].copy(deep=False)
            result[i] = (np.array(result[i]) * ptr["mul"][i]).round(decimals=3)

            mean_result_ptr.append(np.mean(ptr["Result_Append"][i]))
            min_result_ptr.append(np.min(ptr["Result_Append"][i]))
            max_result_ptr.append(np.max(ptr["Result_Append"][i]))
            root_mean_square_ptr.append(np.sqrt(np.mean(np.square(ptr["Result_Append"][i]))))

            ltl = str2float(ptr["LTL"][i])
            utl = str2float(ptr["UTL"][i])

            if ltl == utl == 0:
                test_failed_ptr.insert(i, 0)
            elif (result[i] < ltl).any() or (result[i] > utl).any():
                test_failed_ptr.insert(i, 1)
            else:
                test_failed_ptr.insert(i, 0)

            temp_a = result[i] < ltl
            temp_b = result[i] > utl
            try:
                temp = [a or b for a, b in zip(temp_a, temp_b)]
            except Exception:
                temp = [temp_a or temp_b]
            failed_idx_ptr.insert(i, temp)

            # To find which 'IC' failed in a particular test
            if ltl == utl == 0:
                failed_IC_ptr.insert(i, 0)
            elif any(failed_idx_ptr[i]):
                temp_c = ((np.where(failed_idx_ptr[i])[0]) + 1).tolist()
                failed_IC_ptr.insert(i, temp_c)
            else:
                # '0' means all IC's in a test are passed
                failed_IC_ptr.insert(i, 0)

        ptr = ptr.assign(
            Mean_Value=mean_result_ptr,
            Min_Value=min_result_ptr,
            Max_Value=max_result_ptr,
            RMS=root_mean_square_ptr,
            Test_Failed=test_failed_ptr,
            IC_Failed=failed_IC_ptr,
        )

        # Rounding off the decimal digits to 2 values for easy readability
        ptr[["Mean_Value", "Min_Value", "Max_Value", "RMS"]] = ptr[["Mean_Value", "Min_Value", "Max_Value", "RMS"]].round(decimals=2)
        ptr = ptr[
            [
                "TestNo",
                "Test",
                "LSL",
                "LTL",
                "Result_Append",
                "UTL",
                "USL",
                "Mean_Value",
                "Min_Value",
                "Max_Value",
                "RMS",
                "Test_Failed",
                "IC_Failed",
                "PTR.LO_LIMIT",
                "PTR.HI_LIMIT",
                "PTR.UNITS",
            ]
        ]

        # PREPROCESSING "MPR" DATA
        try:
            mpr = pd.read_hdf(self.hdf5_file, f"/raw_stdf_data/{self.filename}/MPR", mode="a")

            # Renaming columns to simple names
            mpr.rename(columns={"MPR.TEST_NUM": "TestNo", "MPR.RTN_RSLT": "Result", "MPR.TEST_TXT": "Test", "MPR.RSLT_CNT": "Result_Count"}, inplace=True)

            # Sorting the values according to 'TestNo' column
            mpr.sort_values(["TestNo", "PART_INDEX"], inplace=True, ignore_index=True)

            mpr = mpr.drop(
                [
                    "MPR.HEAD_NUM",
                    "MPR.SITE_NUM",
                    "MPR.TEST_FLG",
                    "MPR.PARM_FLG",
                    "MPR.RTN_ICNT",
                    "MPR.RTN_STAT",
                    "MPR.ALARM_ID",
                    "MPR.OPT_FLAG",
                    "MPR.LLM_SCAL",
                    "MPR.HLM_SCAL",
                    "MPR.START_IN",
                    "MPR.INCR_IN",
                    "MPR.RTN_INDX",
                ],
                axis=1,
            )

            # Creating empty lists which will be used in the below operation
            mean_result_mpr = []
            min_result_mpr = []
            max_result_mpr = []
            root_mean_square_mpr = []
            res_split = []
            test_failed_mpr = []
            units = []

            # Converting Byte strings to float values
            for i in range(0, len(mpr)):
                temp1 = mpr["Result"][i].decode().strip("[]").split(",")
                temp2 = list(map(float, temp1))
                temp3 = [round(num, 6) for num in temp2]
                temp4 = mpr["MPR.UNITS"][i].decode()
                units.append(temp4)
                res_split.append(temp3)

                if (res_split[i] < mpr["MPR.LO_LIMIT"][i]).any() or (res_split[i] > mpr["MPR.HI_LIMIT"][i]).any():

                    # Variable to indicate which test has been failed
                    test_failed_mpr.insert(i, 1)
                else:
                    test_failed_mpr.insert(i, 0)

            # Adding 'Result' and 'Test_Failed' columns
            mpr = mpr.assign(Results=res_split, Test_Failed=test_failed_mpr, Units=units)
            mpr = mpr.drop(["Result"], axis=1)

            # Storing 'Mean', 'Maximum', 'Minimum' and 'Root Mean Square' value
            # of test results of a test in 'max_result' variable
            for i in range(0, len(mpr)):
                mean_result_mpr.append(np.mean(mpr["Results"][i]))
                min_result_mpr.append(np.min(mpr["Results"][i]))
                max_result_mpr.append(np.max(mpr["Results"][i]))
                root_mean_square_mpr.append(np.sqrt(np.mean(np.square(mpr["Results"][i]))))

            mpr = mpr.assign(Mean_Value=mean_result_mpr, Min_Value=min_result_mpr, Max_Value=max_result_mpr, RMS=root_mean_square_mpr)

            mpr[["Mean_Value", "Min_Value", "Max_Value", "RMS"]] = mpr[["Mean_Value", "Min_Value", "Max_Value", "RMS"]].round(decimals=2)

            mpr["fmt"] = mpr["MPR.C_HLMFMT"].apply(lambda x: x.decode()[1:])
            fmt = "7.3f"

            # Assigning values 10 to the power of 'mpr.RES_SCAL' column
            mpr["mul"] = 10 ** mpr["MPR.RES_SCAL"].apply(lambda x: float(x))

            # Assigning values from the 'SI' dictionary above to the mpr['mul']
            mpr["SI"] = mpr["mul"].apply(lambda x: self.SI[x])

            mpr["LTL"] = (
                (mpr["MPR.LO_LIMIT"] * mpr["mul"]).apply(lambda x: f"{x:{fmt}} ") + mpr["SI"].apply(lambda x: x) + mpr["MPR.UNITS"].apply(lambda x: x.decode())
            )
            mpr["UTL"] = (
                (mpr["MPR.HI_LIMIT"] * mpr["mul"]).apply(lambda x: f"{x:{fmt}} ") + mpr["SI"].apply(lambda x: x) + mpr["MPR.UNITS"].apply(lambda x: x.decode())
            )
            mpr["Test"] = mpr["Test"].apply(lambda x: x.decode())
            mpr["LSL"] = (
                (mpr["MPR.LO_SPEC"] * mpr["mul"]).apply(lambda x: f"{x:{fmt}} ") + mpr["SI"].apply(lambda x: x) + mpr["MPR.UNITS"].apply(lambda x: x.decode())
            )
            mpr["USL"] = (
                (mpr["MPR.HI_SPEC"] * mpr["mul"]).apply(lambda x: f"{x:{fmt}} ") + mpr["SI"].apply(lambda x: x) + mpr["MPR.UNITS"].apply(lambda x: x.decode())
            )

            mpr["LSL"] = mpr["LSL"].apply(lambda x: x if x.find("inf") < 0 else "")
            mpr["LTL"] = mpr["LTL"].apply(lambda x: x if x.find("inf") < 0 else "")
            mpr["UTL"] = mpr["UTL"].apply(lambda x: x if x.find("inf") < 0 else "")
            mpr["USL"] = mpr["USL"].apply(lambda x: x if x.find("inf") < 0 else "")

            # Re-Arranging the columns in desiered manner
            mpr = mpr[
                [
                    "TestNo",
                    "PART_INDEX",
                    "Test",
                    "Result_Count",
                    "LSL",
                    "LTL",
                    "Results",
                    "UTL",
                    "USL",
                    "Mean_Value",
                    "Min_Value",
                    "Max_Value",
                    "RMS",
                    "Test_Failed",
                    "MPR.LO_LIMIT",
                    "MPR.HI_LIMIT",
                    "Units",
                ]
            ]

        # In-case if there is no 'MPR' data, then it notifies in the PyQt Window
        except Exception:
            mpr = pd.DataFrame(columns=["Test_Failed"])
            mpr["Test_Failed"] = ["MPR", "Data", "is", "Empty"]
            print("MPR field is empty ... ")

        return ptr, mpr


class TableWidget(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.text()) < float(other.text())
        except Exception:
            return QTableWidgetItem.__lt__(self, other)


class Test_Results(QWidget, SpyderWidgetMixin):
    def __init__(self, parent=None, background_color=None):
        if PYQT5:
            super().__init__(parent=parent, class_parent=parent)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        # Loading 'ui' files developed in 'QtDesigner'
        loadUi(__file__.replace(".py", ".ui"), self)

        self.path = ""
        self._filename = ""
        self.filename = ""
        self.ptr_table = []
        self.adjustUI()

        # Connect to the mentioned functions when 'PushButton' is triggered
        self.last_selected_row = -1
        self.clicked_index = []

    def adjustUI(self):
        self.set_column_width()
        self.progressBar.hide()
        self.lstatus.setText("")
        self.llotid.setText("")

    def open_files(self, fname=""):
        path = os.getcwd() if self.path == "" else self.path
        if fname == "" or not fname:
            fname = QFileDialog().getOpenFileName(self, "Open STDF File", path, "stdf Files (*.stdf *.std)")
            fname = fname[0]
            if fname == "":
                return

        self.path, self.filename = os.path.split(fname)
        if not os.path.exists(fname):
            return
        self.progressBar.show()
        QCoreApplication.processEvents()

        # To load Pandas dataframes
        if not self.loaddata():
            self.progressBar.hide()
            return False

        # Generate 'pdf' from the '.json' files
        # self.jsonFile.clicked.connect(self.generate_graph_from_json)

        # To fill 'PTR' data in 'QTableWidget'
        self.fill_ptr_data()

        # To fill 'MPR' data in 'QTableWidget'
        self.fill_mpr_data()

        # Assigning desiered column width to particular columns
        self.set_column_width()

        # To Colour values based on whether test has been passed (PTR Table)
        self.colour_pass_fail_ptr_data()

        # Implement signal function on the event of 'Cell Clicked'
        self.tableWidget_ptr.selectionModel().selectionChanged.connect(self.plot_graph_ptr)

        self.enter_filter_test_name_ptr.textChanged.connect(self.filter_test_name_ptr)
        self.enter_filter_test_name_mpr.textChanged.connect(self.filter_test_name_mpr)
        self.tabWidget.currentChanged.connect(lambda: self.keyPressEvent(None))
        self.last_selected_row = -1
        self.clicked_index = []

        try:
            # To Colour values based on whether test has been passed (MPR)
            self.colour_pass_fail_mpr_data()

            # Implement signal function on the event of 'Cell Clicked'
            self.tableWidget_mpr.selectionModel().selectionChanged.connect(self.plot_select)

        # If there is no 'MPR' data, conditional formatting is not required
        except Exception:
            print("No values to Format in MPR Tab ...")
        self.progressBar.hide()

    # To load Pandas dataframes
    def loaddata(self):
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

    def fill_ptr_data(self):
        # Set no. of rows in PyQt5 Widget
        self.keyPressEvent(None)
        self.tableWidget_ptr.setRowCount(len(self.ptr_table))
        col = 0
        self.progressBar.show()
        for column in self.ptr_table.columns[0:5]:
            row = 0
            for j in range(0, len(self.ptr_table)):
                for val in self.ptr_table[column][[j]]:
                    self.tableWidget_ptr.setItem(row, col, TableWidget(str(val)))
                    row += 1
            col += 1
            self.printProgressBar(col, 17, prefix="Progress PTR:", suffix="Complete", length=50)

        col = 10
        for column in self.ptr_table.columns[5:13]:
            row = 0
            for j in range(0, len(self.ptr_table)):
                for val in self.ptr_table[column][[j]]:
                    self.tableWidget_ptr.setItem(row, col, TableWidget(str(val)))
                    row += 1
            col += 1
            self.printProgressBar(col, 17, prefix="Progress PTR:", suffix="Complete", length=50)
        self.progressBar.hide()

    def filter_test_name_ptr(self, filter_test):
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

    # To fill 'MPR' data in 'QTableWidget'
    def fill_mpr_data(self):
        # Set no. of rows in PyQt5 Widget
        self.keyPressEvent(None)
        self.progressBar.show()
        self.tableWidget_mpr.setRowCount(len(self.mpr_table))
        col = 0
        for column in self.mpr_table.columns[0:14]:
            row = 0
            for j in range(0, len(self.mpr_table)):
                for val in self.mpr_table[column][[j]]:
                    # self.tableWidget_mpr.setItem(row, col, QtWidgets.QTableWidgetItem(str(val)))
                    self.tableWidget_mpr.setItem(row, col, TableWidget(str(val)))
                    row += 1
            col += 1
            self.printProgressBar(col, len(self.mpr_table.columns) - 3, prefix="Progress MPR:", suffix="Complete", length=50)
        self.progressBar.hide()

    def filter_test_name_mpr(self, filter_test):
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

    # Action function on the event of 'Cell Clicked' in QTableWidget
    def plot_select(self, selected):
        if len(selected.indexes()) > 0:
            self.last_selected_row = selected.indexes()[0].row()
        else:
            print('no row selected')

    # To open menu on Right-Click
    def contextMenuEvent(self, event):
        if self.tableWidget_mpr.selectionModel().selection().indexes():
            menu = QMenu(self)
            plotAction = menu.addAction("Plot Graph") if self.clicked_index != [] else None
            addAction = menu.addAction("Add Graph")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == plotAction:
                self.graph_show()
            elif action == addAction and self.last_selected_row != -1 and self.last_selected_row not in self.clicked_index:
                self.clicked_index.append(self.last_selected_row)
                self.lstatus.setText(f'line {[i+1 for i in self.clicked_index]} selected')

    # Function to plot graph
    def graph_show(self):
        try:
            if len(self.clicked_index) == 1:
                # plt.clf()
                plt.autoscale(True)
                plt.figure(figsize=(3.2, 2.4), dpi=200)
                plt.title(self._filename + " \\ " + self.lot + "\n")

                ylabel = self.mpr_table["Test"][self.clicked_index[0]]
                ylabel = f'{ylabel}\n ({self.mpr_table["Units"][self.clicked_index[0]]})'
                #if len(si.split(" ")) > 1:
                #    ylabel = f'{ylabel}\n ({si.split(" ")[1]})'
                # plt.ylabel(self.mpr_table["Units"][self.clicked_index[0]])
                plt.ylabel(ylabel, rotation=90)

                ltl = self.mpr_table["MPR.LO_LIMIT"][self.clicked_index[0]]
                utl = self.mpr_table["MPR.HI_LIMIT"][self.clicked_index[0]]
                if ltl not in [-np.inf, np.inf]:
                    plt.hlines(self.mpr_table["MPR.LO_LIMIT"][self.clicked_index[0]], 0, self.mpr_table["Result_Count"][self.clicked_index[0]], color="r")
                if utl not in [-np.inf, np.inf]:
                    plt.hlines(self.mpr_table["MPR.HI_LIMIT"][self.clicked_index[0]], 0, self.mpr_table["Result_Count"][self.clicked_index[0]], color="r")
                plt.hlines(self.mpr_table["Min_Value"][self.clicked_index[0]], 0, self.mpr_table["Result_Count"][self.clicked_index[0]], color="m")
                plt.hlines(self.mpr_table["Max_Value"][self.clicked_index[0]], 0, self.mpr_table["Result_Count"][self.clicked_index[0]], color="m")
                plt.hlines(self.mpr_table["Mean_Value"][self.clicked_index[0]], 0, self.mpr_table["Result_Count"][self.clicked_index[0]], color="y")
                # plt.plot(results, "bo", markersize=0.1, alpha=0.1)
                plt.plot(self.mpr_table["Results"][self.clicked_index[0]], "bo-", markeredgecolor="magenta", markersize=1)
                # plt.legend([self.mpr_table["Test"][self.clicked_index[0]], "LTL and UTL", "_nolegend_", "Min and Max", "_nolegend_", "Mean"])

            elif len(self.clicked_index) == 2:
                # label_a = self.mpr_table["Units"][self.clicked_index[0]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[0]]) + "]"
                # label_b = self.mpr_table["Units"][self.clicked_index[1]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[1]]) + "]"
                # temp_c = temp_a + " vs " + temp_b

                plt.figure(figsize=(3.2, 2.4), dpi=200)
                # plt.plot(self.mpr_table["Results"][self.clicked_index[0]], self.mpr_table["Results"][self.clicked_index[1]], "go", markersize=0.3, alpha=0.5)
                # plt.title(self._filename + " \\ " + self.lot + "\n" + self.mpr_table["Test"][self.clicked_index[0]])
                plt.title(self._filename + " \\ " + self.lot + "\n")
                # plt.xlabel(self.mpr_table["Units"][self.clicked_index[0]])
                # plt.ylabel(self.mpr_table["Units"][self.clicked_index[1]])
                # plt.legend([temp_c])
                plt.plot(self.mpr_table["Results"][self.clicked_index[0]], "go-", markersize=0.3, alpha=0.5)
                plt.plot(self.mpr_table["Results"][self.clicked_index[1]], "ro-", markersize=0.3, alpha=0.5)
                label_0 = self.mpr_table["Test"][self.clicked_index[0]]
                label_1 = self.mpr_table["Test"][self.clicked_index[1]]
                plt.ylabel(f'{self.mpr_table["Units"][self.clicked_index[0]]}', rotation=90)
                plt.legend([label_0, label_1])

            elif len(self.clicked_index) == 3:
                temp_a = self.mpr_table["Units"][self.clicked_index[0]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[0]]) + "]"
                temp_b = self.mpr_table["Units"][self.clicked_index[1]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[1]]) + "]"
                temp_c = temp_a + " vs " + temp_b
                temp_d = self.mpr_table["Units"][self.clicked_index[2]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[2]]) + "]"
                temp_e = temp_a + " vs " + temp_d

                plt.figure(figsize=(3.2, 2.4), dpi=200)
                plt.plot(self.mpr_table["Results"][self.clicked_index[0]], self.mpr_table["Results"][self.clicked_index[1]], "go", markersize=0.1, alpha=0.5)
                plt.plot(self.mpr_table["Results"][self.clicked_index[0]], self.mpr_table["Results"][self.clicked_index[2]], "ro", markersize=0.1, alpha=0.5)
                plt.title(self._filename + " \\ " + self.lot + "\n" + self.mpr_table["Test"][self.clicked_index[0]])
                plt.xlabel(self.mpr_table["Units"][self.clicked_index[0]])
                plt.ylabel(self.mpr_table["Units"][self.clicked_index[1]] + "   /   " + self.mpr_table["Units"][self.clicked_index[2]])
                plt.legend([temp_c, temp_e])

            elif len(self.clicked_index) == 4:
                temp_a = self.mpr_table["Units"][self.clicked_index[0]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[0]]) + "]"
                temp_b = self.mpr_table["Units"][self.clicked_index[1]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[1]]) + "]"
                temp_c = temp_a + " vs " + temp_b
                temp_d = self.mpr_table["Units"][self.clicked_index[2]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[2]]) + "]"
                temp_e = temp_a + " vs " + temp_d
                temp_f = self.mpr_table["Units"][self.clicked_index[3]] + "[" + str(self.mpr_table["PART_INDEX"][self.clicked_index[3]]) + "]"
                temp_g = temp_a + " vs " + temp_f

                plt.figure(figsize=(3.2, 2.4), dpi=200)
                plt.plot(
                    self.mpr_table["Results"][self.clicked_index[0]],
                    self.mpr_table["Results"][self.clicked_index[1]],
                    "go",
                    markersize=0.1,
                    alpha=0.5,
                    label=temp_c,
                )
                plt.plot(
                    self.mpr_table["Results"][self.clicked_index[0]],
                    self.mpr_table["Results"][self.clicked_index[2]],
                    "ro",
                    markersize=0.1,
                    alpha=0.5,
                    label=temp_e,
                )
                plt.plot(
                    self.mpr_table["Results"][self.clicked_index[0]],
                    self.mpr_table["Results"][self.clicked_index[3]],
                    "yo",
                    markersize=0.1,
                    alpha=0.5,
                    label=temp_g,
                )
                plt.title(self.mpr_table["Test"][self.clicked_index[0]])
                plt.xlabel(self.mpr_table["Units"][self.clicked_index[0]])
                plt.ylabel(
                    self.mpr_table["Units"][self.clicked_index[1]]
                    + "   /   "
                    + self.mpr_table["Units"][self.clicked_index[2]]
                    + "   /   "
                    + self.mpr_table["Units"][self.clicked_index[3]]
                )
                plt.legend([temp_c, temp_e, temp_g])

            else:
                pass

            plt.show()

        except ValueError:
            plt.title("Result Count must match ... ")
            print("Result Count must match ... ")
            plt.show()

        self.clicked_index.clear()
        self.lstatus.setText('')
        self.last_selected_row = -1

    # Function to plot graph in PTR Tab
    def plot_graph_ptr(self, selected):
        if len(selected.indexes()) == 0:
            self.lstatus.setText('')
            return
        selectIndex = selected.indexes()[0].row()
        # testNo = int(self.tableWidget_ptr.item(selectIndex, 0).text())
        index = selectIndex
        self.lstatus.setText(f'ptr line {index+1} selected')

        plt.clf()
        plt.autoscale(True)
        ltl = str2float(self.tableWidget_ptr.item(selectIndex, TaPtrItems["LTL"]).text())
        utl = str2float(self.tableWidget_ptr.item(selectIndex, TaPtrItems["UTL"]).text())
        results = self.tableWidget_ptr.item(selectIndex, TaPtrItems["Results"]).text()[1:-1].split(" ")
        data = []
        for value in results:
            if value != "":
                data.append(str2float(value))
        if ltl != utl:
            plt.hlines(ltl, 0, len(data)-1, color="r")
            plt.hlines(utl, 0, len(data)-1, color="r")
        plt.plot(data, "bo-", markeredgecolor="magenta", markersize=3)
        plt.title(self._filename + " \\ " + self.lot + "\n")
        plt.xlabel("Part Index")
        si = self.tableWidget_ptr.item(selectIndex, TaPtrItems["LTL"]).text().strip()
        ylabel = self.tableWidget_ptr.item(selectIndex, TaPtrItems["Test Name"]).text()
        if len(si.split(" ")) > 1:
            ylabel = f'{ylabel}\n ({si.split(" ")[1]})'
        plt.ylabel(ylabel, rotation=90)

    @property
    def filename(self):
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
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + "-" * (length - filledLength)
        self.update_Progress_bar(iteration, total)
        # print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)
        # if iteration == total:
        #    print()

    def update_Progress_bar(self, count, maxcount):
        self.progressBar.setRange(1, maxcount)
        self.progressBar.setValue(count)
        QCoreApplication.processEvents()

    # Trigger Function to close the window
    def close_window(self):
        self.close()

    # 'Esc' key event to reset the click counter if unknowingly pressed
    def keyPressEvent(self, event):
        print("Esc")
        if event is None or event.key() == Qt.Key_Escape:
            self.last_selected_row = -1
            self.clicked_index.clear()
            self.lstatus.setText('')
        elif event is not None and event.key() == Qt.Key_Return:
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
