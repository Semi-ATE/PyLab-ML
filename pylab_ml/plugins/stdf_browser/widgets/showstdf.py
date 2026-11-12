# -*- coding: utf-8 -*-

"""
This script contains the 'showStdf' class which is used to convert the '.stdf' file into '.hdf5' file and
then preprocess the data to fill in the 'QTableWidget' in the PyQt window. It also contains the 'Test_Results' class
which is used to display the preprocessed data in the PyQt window and also to generate graphs from the data.
"""

# Standard library imports
import os
from pathlib import Path

# Third library imports
from Metis.tools import stdf2ph5, STDFHelper
import pandas as pd
import numpy as np


def str2float(string):
    """
    This function is used to convert the string value of 'LTL' and 'UTL' columns to float values for comparison with the test results.

    eg. str2float("1.234 kV") will return 1234.0

    Parameters
    ----------
        string : str
            The string value of 'LTL' or 'UTL' column, which contains the value along with the SI unit and the unit of measurement.

    Returns
    -------
        float
            The float value of the input string after removing the SI unit and the unit of measurement.
    """
    result = string.strip().split(" ")
    return float(result[0])


class showStdf:
    """
    This class is used to convert the '.stdf' file into '.hdf5' file and
    then preprocess the data to fill in the 'QTableWidget' in the PyQt window. It also contains methods
    to display the preprocessed data in the PyQt window and to generate graphs from the data.
    """

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
        """
        Initializes the showStdf class with the given parameters and checks if the corresponding '.hdf5' file already exists.
        If it exists and is older than the '.stdf' file, it removes the '.hdf5' file to ensure that the data is updated when the '.stdf' file is processed again.

        Parameters
        ----------
            path : str
                The directory path where the '.stdf' file is located.
            filename : str
                The name of the '.stdf' file.
            lot : str
                The lot identifier.
            resultdir : str
                The directory where the '.hdf5' file will be stored.
            update_Progress_bar : callable, optional
                A function to update the progress bar, if provided.
        """
        self.hdf5_file = f"{path}/{self.RESULTDIR}/{lot}.h5"
        self.filename = filename
        self.path = path
        self.resultdir = resultdir
        self.update_Progress_bar = update_Progress_bar
        self.ptr_table = []
        self.mpr_table = []

        if Path(self.hdf5_file).is_file() and os.path.getmtime(path + "/" + filename) > os.path.getmtime(self.hdf5_file):
            os.remove(self.hdf5_file)

    def init(self):
        """
        This method checks if the corresponding '.hdf5' file already exists.
        If it does not exist, it converts the '.stdf' file into '.hdf5' file using the 'stdf2ph5' module and stores it in the specified directory.

        Returns
        -------
            bool
                True if the '.hdf5' file exists or was successfully created, False otherwise.
        """
        if not Path(self.hdf5_file).is_file():
            stdf = stdf2ph5.SHP(False, update_progress=self.update_Progress_bar)
            if not STDFHelper.is_plain_stdf(f"{self.path}/{self.filename}"):
                return False
            stdf.import_stdf_into_hdf5(f"{self.path}/{self.filename}", f"{self.path}/{self.resultdir}", disable_progress=True)
        return True

    # Function to convert '.hd5' to Pandas dataframe
    def raw_hdf5_data(self):
        """
        This method reads the raw HDF5 data and preprocesses it for further analysis.

        Returns
        -------
            pd.DataFrame
                The preprocessed data as a Pandas DataFrame.
        """
        # PREPROCESSING "PTR" DATA
        try:
            ptr = pd.read_hdf(self.hdf5_file, f"/raw_stdf_data/{self.filename}/PTR", mode="a")
        except (KeyError, FileNotFoundError):
            ptr = None

        if ptr is None or ptr.empty:
            ptr = pd.DataFrame()
        else:
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
            ptr2.drop(columns=ptr2.columns[0], inplace=True)

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
                axis = 1
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
