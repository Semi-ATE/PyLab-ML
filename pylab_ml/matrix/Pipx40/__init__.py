import pyvisa as visa
import platform
from ctypes import *
from array import array


def tohex(val, nbits):
    return hex((val + (1 << nbits)) % (1 << nbits))


def Version():
    return "2020.04.08"


def calc_dwords(bits):
    dwords = bits / 32
    dwords = int(dwords)
    if bits % 32 > 0:
        dwords = dwords + 1
    return dwords


class pipx40_base:

    def __init__(self):
        self.rm = visa.ResourceManager()
        arch = platform.architecture()

        # ctypes.util.find_library() fixes issue loading pipx40 DLL under Python 3
        # without full path
        if "64bit" in arch:
            library = util.find_library("pipx40_64")
            self.handle = windll.LoadLibrary(library)
        else:
            library = util.find_library("pipx40_32")
            self.handle = windll.LoadLibrary(library)

    def FindFreeCards(self):
        resource_list = []

        # Array of available resources
        resources = self.rm.list_resources()
        x = 0
        for resource in resources:
            if 'PXI' in resource:
                resource_list.insert(x, resource)
                x = x + 1
        return resource_list

    def CountFreeCards(self):
        resource_list = pipx40_base.FindFreeCards(self)
        return resource_list.__len__()

    def __del__(self):
        self.rm.close()  # deletes session
        del self.handle  # deletes the handle


class pipx40_card(pipx40_base):

    def __init__(self, rsrcName, id_query, reset_instr):
        pipx40_base.__init__(self)
        self.vi = c_uint32(0)
        resource = rsrcName.encode()
        err = self.handle.pipx40_init(resource, id_query, reset_instr, byref(self.vi))

        # Raise a ValueError exception if opening the card fails
        if err:
            err, errorString = self.ErrorMessage(err)
            raise ValueError(errorString)

        # Resistor card capabilities flags
        self.RESCAP = {
            "RES_CAP_NONE": 0x00,
            "RES_CAP_PREC": 0x01,
            "RES_CAP_ZERO": 0x02,
            "RES_CAP_INF":  0x04,
            "RES_CAP_REF":  0x08
        }

        # Error codes Enum
        ERROR_BASE = 0xBFFC0800  # 3220965376
        self.ERRORCODE = {
            "ERROR_BAD_SESSION":                (ERROR_BASE + 0x00),  # Not a valid pipx40 session
            "ERROR_NO_INFO":                    (ERROR_BASE + 0x01),  # Card information unobtainable - hardware problem
            "ERROR_CARD_DISABLED":              (ERROR_BASE + 0x02),  # Card disabled - hardware problem
            "ERROR_BAD_SUB":                    (ERROR_BASE + 0x03),  # Card has no sub-unit with specified number
            "ERROR_BAD_CHANNEL":                (ERROR_BASE + 0x04),  # Sub-unit has no channel with specified number
            "ERROR_NO_CAL_DATA":                (ERROR_BASE + 0x05),  # Sub-unit has no calibration data to write/read
            "ERROR_BAD_ARRAY":                  (ERROR_BASE + 0x06),  # Array type, size or shape is incorrect
            "ERROR_MUX_ILLEGAL":                (ERROR_BASE + 0x07),  # Non-zero write data is illegal for MUX sub-unit
            "ERROR_EXCESS_CLOSURE":             (ERROR_BASE + 0x08),  # Sub-unit closure limit exceeded
            "ERROR_ILLEGAL_MASK":               (ERROR_BASE + 0x09),  # One or more of the specified channels cannot be masked
            "ERROR_OUTPUT_MASKED":              (ERROR_BASE + 0x0A),  # Cannot activate an output that is masked
            "ERROR_FAILED_INIT":                (ERROR_BASE + 0x0B),  # Cannot open a Pickering card with this resource name
            "ERROR_READ_FAIL":                  (ERROR_BASE + 0x0C),  # Failed read from hardware
            "ERROR_WRITE_FAIL":                 (ERROR_BASE + 0x0D),  # Failed write to hardware
            "ERROR_VISA_OP":                    (ERROR_BASE + 0x0E),  # VISA operation failed
            "ERROR_VISA_VERSION":               (ERROR_BASE + 0x0F),  # Incompatible VISA version
            "ERROR_SUB_TYPE":                   (ERROR_BASE + 0x10),  # Function call incompatible with sub-unit type or capabilities
            "ERROR_BAD_ROW":                    (ERROR_BASE + 0x11),  # Matrix row value out of range
            "ERROR_BAD_COLUMN":                 (ERROR_BASE + 0x12),  # Matrix column value out of range
            "ERROR_BAD_ATTEN":                  (ERROR_BASE + 0x13),  # Attenuation value out of range
            "ERROR_BAD_VOLTAGE":                (ERROR_BASE + 0x14),  # Voltage value out of range
            "ERROR_BAD_CAL_INDEX":              (ERROR_BASE + 0x15),  # Calibration reference out of range
            "ERROR_BAD_SEGMENT":                (ERROR_BASE + 0x16),  # Segment number out of range
            "ERROR_BAD_FUNC_CODE":              (ERROR_BASE + 0x17),  # Function code value out of range
            "ERROR_BAD_SUBSWITCH":              (ERROR_BASE + 0x18),  # Subswitch value out of range
            "ERROR_BAD_ACTION":                 (ERROR_BASE + 0x19),  # Action code out of range
            "ERROR_STATE_CORRUPT":              (ERROR_BASE + 0x1A),  # Cannot execute due to corrupt sub-unit state
            "ERROR_BAD_ATTR_CODE":              (ERROR_BASE + 0x1B),  # Unrecognised attribute code
            "ERROR_EEPROM_WRITE_TMO":           (ERROR_BASE + 0x1C),  # Timeout writing to EEPROM
            "ERROR_ILLEGAL_OP":                 (ERROR_BASE + 0x1D),  # Operation is illegal in the sub-unit's current state
            "ERROR_BAD_POT":                    (ERROR_BASE + 0x1E),  # Unrecognised pot number requested
            "ERROR_MATRIXR_ILLEGAL":            (ERROR_BASE + 0x1F),  # Invalid write pattern for MATRIXR sub-unit
            "ERROR_MISSING_CHANNEL":            (ERROR_BASE + 0x20),  # Attempted operation on non-existent channel
            "ERROR_CARD_INACCESSIBLE":          (ERROR_BASE + 0x21),  # Card cannot be accessed (failed/removed/unpowered)
            "ERROR_BAD_FP_FORMAT":              (ERROR_BASE + 0x22),  # Unsupported internal floating-point format (internal error)
            "ERROR_UNCALIBRATED":               (ERROR_BASE + 0x23),  # Sub-unit is not calibrated
            "ERROR_BAD_RESISTANCE":             (ERROR_BASE + 0x24),  # Unobtainable resistance value
            "ERROR_BAD_STORE":                  (ERROR_BASE + 0x25),  # Invalid calibration store number
            "ERROR_BAD_MODE":                   (ERROR_BASE + 0x26),  # Invalid mode value
            "ERROR_SETTINGS_CONFLICT":          (ERROR_BASE + 0x27),  # Conflicting device settings
            "ERROR_CARD_TYPE":                  (ERROR_BASE + 0x28),  # Function call incompatible with card type or capabilities
            "ERROR_BAD_POLE":                   (ERROR_BASE + 0x29),  # Switch pole value out of range
            "ERROR_MISSING_CAPABILITY":         (ERROR_BASE + 0x2A),  # Attempted to activate a non-existent capability
            "ERROR_MISSING_HARDWARE":           (ERROR_BASE + 0x2B),  # Action requires hardware that is not present
            "ERROR_HARDWARE_FAULT":             (ERROR_BASE + 0x2C),  # Faulty hardware
            "ERROR_EXECUTION_FAIL":             (ERROR_BASE + 0x2D),  # Failed to execute (e.g. blocked by a hardware condition)
            "ERROR_BAD_CURRENT":                (ERROR_BASE + 0x2E),  # Current value out of range
            "ERROR_BAD_RANGE":                  (ERROR_BASE + 0x2F),  # Invalid range value
            "ERROR_ATTR_UNSUPPORTED":           (ERROR_BASE + 0x30),  # Attribute not supported
            "ERROR_BAD_REGISTER":               (ERROR_BASE + 0x31),  # Register number out of range
            "ERROR_MATRIXP_ILLEGAL":            (ERROR_BASE + 0x32),  # Invalid channel closure or write pattern for MATRIXP sub-unit
            "ERROR_BUFFER_UNDERSIZE":           (ERROR_BASE + 0x33),  # Data buffer too small
            "ERROR_ACCESS_MODE":                (ERROR_BASE + 0x34),  # Inconsistent shared access mode
            "ERROR_POOR_RESISTANCE":            (ERROR_BASE + 0x35),  # Resistance outside limits
            "ERROR_BAD_ATTR_VALUE ":            (ERROR_BASE + 0x36),  # Bad attribute value
            "ERROR_INVALID_POINTER":            (ERROR_BASE + 0x37),  # Invalid pointer
            "ERROR_ATTR_READ_ONLY":             (ERROR_BASE + 0x38),  # Attribute is read only
            "ERROR_ATTR_DISABLED":              (ERROR_BASE + 0x39),  # Attribute is disabled
            "ERROR_PSU_MAIN_DISABLED":          (ERROR_BASE + 0x3A),  # Main output is disabled, cannot enable the channel
            "ERROR_OUT_OF_MEMORY_HEAP":         (ERROR_BASE + 0x3B),  # Unable to allocate memory on Heap
            "ERROR_INVALID_PROCESSID":          (ERROR_BASE + 0x3C),  # Invalid ProcessID
            "ERROR_SHARED_MEMORY":              (ERROR_BASE + 0x3D),  # Shared memory error
            "ERROR_CARD_OPENED_OTHER_PROCESS":  (ERROR_BASE + 0x3E),  # Card is opened by a process in exclusive mode
            "ERROR_UNKNOWN":                    (ERROR_BASE + 0x7FF)  # Unknown error code
        }
        # Attribute Codes Enum
        self.ATTR = {
            "TYPE": 0x400,  # Gets/Sets DWORD attribute value of Type of the Sub-unit (values: TYPE_MUXM, TYPE_MUXMS)
            "MODE": 0x401,  # Gets/Sets DWORD attribute value of Mode of the Card

            # Current monitoring attributes
            "CNFGREG_VAL": 0x402,  # Gets/Sets WORD value of config register
            "SHVLREG_VAL": 0x403,  # Gets WORD value of shuntvoltage register
            "CURRENT_VAL": 0x404,  # Gets double current value in Amps

            # Read-only Power Supply attributes
            "INTERLOCK_STATUS": 0x405,  # Gets BOOL value of interlock status
            "OVERCURRENT_STATUS_MAIN": 0x406,  # Gets BOOL value of main overcurrent status
            "OVERCURRENT_STATUS_CH": 0x407,  # Gets BOOL value of overcurrent status on specific channel

            # Read/Write Power Supply attributes
            "OUTPUT_ENABLE_MAIN": 0x408,  # Gets/Sets BOOL value. Enables/Disables main
            "OUTPUT_ENABLE_CH": 0x409,  # Gets/Sets BOOL value. Enables/Disables specific channel

            # Read/Write Thermocouple Simulator functions
            "TS_SET_RANGE": 0x40A,  # Gets/Sets Auto range which toggles between based on the value
            # Read-only function
            "TS_LOW_RANGE_MIN": 0x40B,
            "TS_LOW_RANGE_MED": 0x40C,
            "TS_LOW_RANGE_MAX": 0x40D,
            "TS_LOW_RANGE_MAX_DEV": 0x40E,
            "TS_LOW_RANGE_PREC_PC": 0x40F,
            "TS_LOW_RANGE_PREC_DELTA": 0x410,
            "TS_MED_RANGE_MIN": 0x411,
            "TS_MED_RANGE_MED": 0x412,
            "TS_MED_RANGE_MAX": 0x413,
            "TS_MED_RANGE_MAX_DEV": 0x414,
            "TS_MED_RANGE_PREC_PC": 0x415,
            "TS_MED_RANGE_PREC_DELTA": 0x416,
            "TS_HIGH_RANGE_MIN": 0x417,
            "TS_HIGH_RANGE_MED": 0x418,
            "TS_HIGH_RANGE_MAX": 0x419,
            "TS_HIGH_RANGE_MAX_DEV": 0x41A,
            "TS_HIGH_RANGE_PREC_PC": 0x41B,
            "TS_HIGH_RANGE_PREC_DELTA": 0x41C,
            "TS_POT_VAL": 0x41D,  # Read Pot Value from user store
            # Write-only function
            "TS_SET_POT": 0x41E,
            "TS_SAVE_POT": 0x41F,
            "TS_DATA_DUMP": 0x420,
            "MUXM_MBB": 0x421,

            # LVDT Mk2 Set only
            "LVDT_RESET": 0x422,  # Initialise LVDT card with calibration values
            "LVDT_CHANNEL_AUTO_PHASE": 0x423,  # 'AP' Measures frequency then applies delay
            "LVDT_AUTO_INPUT_ATTEN": 0x424,  # 'AG' Sets the input potentiometer to 95%
            "LVDT_CHANNEL_INVERT": 0x439,  # 'IV' invert channel(s)
            "LVDT_PHASE_TRACKING": 0x43A,  # 'TP' Phase tracking mode on or off
            "LVDT_PERIOD_COUNTS": 0x43B,  # Set the delay between counts
            "LVDT_SAMPLE_LOAD": 0x43C,  # 'SL' Sample Load function

            # LVDT Mk2 Set/Get
            "LVDT_CHANNEL_POSITION": 0x425,  # 'SA' Absolute position in mode 1
            "LVDT_CHANNEL_MODE2_POSITION": 0x426,  # 'SAA' or 'SAB' Absolute position in mode 2
            "LVDT_CHANNEL_PERCENT_POSITION": 0x427,  # 'SP' Percent position mode 1
            "LVDT_CHANNEL_MODE2_PERCENT_POSITION": 0x428,  # 'SPA' or 'SPB' Percent position mode 2
            "LVDT_CHANNEL_VOLTAGE_SUM": 0x429,  # 'VS' Vsum in milliVolts
            "LVDT_CHANNEL_VOLTAGE_DIFF": 0x42A,  # 'VD' Vdiff in milliVolts
            "LVDT_CHANNEL_OUT_GAIN": 0x42B,  # 'OG' x1 or x2 output multiplier
            "LVDT_MANUAL_INPUT_ATTEN": 0x42C,  # 'P' Manually adjust input potentiometer to specified number
            "LVDT_CHANNEL_MODE": 0x42D,  # 'M' mode
            "LVDT_CHANNEL_DELAY": 0x432,  # Delay for both in mode 1 or A in mode 2
            "LVDT_CHANNEL_MODE2_DELAY": 0x433,  # Delay for B in mode 2
            "LVDT_CHANNEL_OUT_LEVEL": 0x437,  # 'OL' output level
            "LVDT_CHANNEL_INPUT_LEVEL": 0x434,  # 'IL' input level invert
            "LVDT_CHANNEL_INPUT_FREQ": 0x435,  # 'IF' read input frequency
            "LVDT_CALIBRATION_VALUES": 0x436,  # 'CV' read calibration values
            "LVDT_CLOCK_DIVIDER": 0x440,  # 'C' set clock divider value

            # LVDT Mk2 Get only
            "LVDT_DSPIC_VERSION": 0x438,  # 'V' read dsPIC version
            "LVDT_CHANNEL_INPUT_FREQ_HI_RES": 0x441,  # 'IF' read input frequency

            "TS_TEMPERATURES_C": 0x42E,  # Read 7 sensors on 1192r0 41-760 I2C Compensation Block in degrees Celsius
            "TS_TEMPERATURES_F": 0x42F,  # Read 7 sensors on 1192r0 41-760 I2C Compensation Block in degrees Farenheit
            "TS_EEPROM": 0x430,  # Read/write 34LC02 eeprom
            "TS_EEPROM_OFFSET": 0x431,  # Supply offset to eeprom

            "CARD_PCB_NUM": 0x43D,  # Card PCB Number.
            "CARD_PCB_REV_NUM": 0x43E,  # Card PCB Revision Number.
            "CARD_FW_REV_NUM": 0x43F  # Card FPGA Firmware Revision Number.
        }

        # Vsource Range Enum
        self.TS_RANGE = {
            "AUTO": 0,
            "LOW": 1,
            "MED": 2,
            "HIGH": 3
        }

        # Card status bits enum
        self.STAT = {
            "STAT_NO_CARD ": 0x80000000,            # No Pickering card open on the session
            "STAT_WRONG_DRIVER ": 0x40000000,       # Card requires later driver version
            "STAT_EEPROM_ERR ": 0x20000000,         # Error interpreting card EEPROM data
            "STAT_DISABLED ": 0x10000000,           # Card is disabled
            "STAT_NO_SUB ": 0x08000000,             # Card has no sub-unit with specified number
            "STAT_BUSY ": 0x04000000,               # Busy (card or sub-unit)
            "STAT_HW_FAULT ": 0x02000000,           # Hardware fault (eg. defective serial loop)
            "STAT_PARITY_ERROR ": 0x01000000,       # PCIbus parity error
            "STAT_PSU_INHIBITED ": 0x00800000,      # PSU sub-unit - supply is disabled (by software)
            "STAT_PSU_SHUTDOWN ": 0x00400000,       # PSU sub-unit - supply is shutdown (due to overload)
            "STAT_PSU_CURRENT_LIMIT ": 0x00200000,  # PSU sub-unit - supply is operating in current-limited mode
            "STAT_CORRUPTED ": 0x00100000,          # Sub-unit logical state is corrupted
            "STAT_CARD_INACCESSIBLE ": 0x00080000,  # Card cannot be accessed (failed/removed/unpowered)
            "STAT_UNCALIBRATED ": 0x00040000,       # Calibration data is faulty (card or sub-unit)
            "STAT_CALIBRATION_DUE": 0x00020000,     # Calibration is due (card or sub-unit)
            "STAT_BIRST_ENABLED ": 0x00010000,      # BIRST is active (card or sub-unit)
            "STAT_OK ": 0x00000000
        }

        # Output subunit type specifier codes
        self.TYPE = {
            "TYPE_SW": 1,       # Uncommitted switches
            "TYPE_MUX": 2,      # Relay multiplexer (single-channel only)
            "TYPE_MUXM": 3,     # Relay multiplexer (multi-channel capable)
            "TYPE_MAT": 4,      # Standard matrix
            "TYPE_MATR": 5,     # RF matrix
            "TYPE_DIG": 6,      # Digital outputs
            "TYPE_RES": 7,      # Programmable Resistor
            "TYPE_ATTEN": 8,    # Programmable Attenuator
            "TYPE_PSUDC": 9,    # Power supply - DC
            "TYPE_BATT": 10,    # Battery simulator
            "TYPE_VSOURCE": 11, # Programmable voltage source
            "TYPE_MATP": 12,    # Matrix with restricted operating modes
            "TYPE_MUXMS": 13,   # Relay multiplexer (MUXM hardware emulated as MUX)
            "TYPE_FI": 14,      # Fault insertion sub-unit
            "TYPE_LVDT": 15,    # LVDT simulator
        }

    # Card Function
    def GetCardId(self):
        strng = create_string_buffer(100)
        err = self.handle.pipx40_getCardId(self.vi, byref(strng))
        return err, str(strng.value.decode())

    def ClearCard(self):
        err = self.handle.pipx40_clearCard(self.vi)
        return err

    def Close(self):
        err = self.handle.pipx40_close(self.vi)
        return err

    def Reset(self):
        err = self.handle.pipx40_reset(self.vi)
        return err

    def SelfTest(self):
        err = self.handle.pipx40_self_test(self.vi, byref(test_result), byref(message))
        return err, test_result.value, message.value

    def RevisionQuery(self):
        err = self.handle.pipx40_revision_query(self.vi, byref(driver_ver), byref(instr_ver))
        return err, driver_ver.value, instr_ver.value

    def Diagnostic(self):
        strng = create_string_buffer(100)
        err = self.handle.pipx40_getDiagnostic(self.vi, byref(strng))
        return err, str(strng.value.decode())

    # Sub-Unit Functions
    def ClearSub(self, sub):
        err = self.handle.pipx40_clearSub(self.vi, sub)
        return err

    def GetClosureLimit(self, sub):
        limit = c_uint(0)
        err = self.handle.pipx40_getClosureLimit(self.vi, sub, byref(limit))
        return err, limit.value

    def GetSubCounts(self):
        ins = c_uint(0)
        outs = c_uint(0)
        err = self.handle.pipx40_getSubCounts(self.vi, byref(ins), byref(outs))
        return err, ins.value, outs.value

    def SubAttribute(self, sub, out_not_in, code):
        attr = c_uint(0)
        err = self.handle.pipx40_getSubAttribute(self.vi, sub, out_not_in, code, byref(attr))
        return err, attr.value

    def SubInfo(self, sub, out_not_in):
        stype = c_uint(0)
        rows = c_uint(0)
        cols = c_uint(0)
        err = self.handle.pipx40_getSubInfo(self.vi, sub, out_not_in, byref(stype), byref(rows), byref(cols))
        return err, stype.value, rows.value, cols.value

    def SubSize(self, sub, out_not_in):
        e, t, r, c = self.SubInfo(sub, out_not_in)
        bits = r * c
        dwords = calc_dwords(bits)
        return dwords, bits

    def SubStatus(self, sub):
        status = c_uint(0)
        err = self.handle.pipx40_getSubStatus(self.vi, sub, byref(status))
        return err, status.value

    def SubType(self, sub, out_not_in):
        strng = create_string_buffer(100)
        err = self.handle.pipx40_getSubType(self.vi, sub, out_not_in, byref(strng))
        return err, str(strng.value.decode())

    def ErrorMessage(self, code):
        s = create_string_buffer(100)
        err = self.handle.pipx40_error_message(self.vi, code, byref(s))
        return code, str(s.value.decode())

    def SetDriverMode(self, mode):
        oldmode = c_uint(0)
        err = self.handle.pipx40_setDriverMode(mode, byref(oldmode))
        return err, oldmode.value

    def GetSettlingTime(self, sub):
        time = c_uint(0)
        err = self.handle.pipx40_getSettlingTime(self.vi, sub, byref(time))
        return err, time.value

    def GetCardStatus(self):
        status = c_uint(0)
        err = self.handle.pipx40_getCardStatus(self.vi, byref(status))
        return err, status

    # Mask Functions

    def SetMaskState(self, sub, bit, action):
        err = self.handle.pipx40_setMaskState(self.vi, sub, bit, action)
        return err

    def SetCrosspointMask(self, sub, row, column, action):
        err = self.handle.pipx40_setCrosspointMask(self.vi, sub, row, column, action)
        return err

    def SetMaskPattern(self, sub, data):
        dta = (c_uint * len(data))()
        for i in range(len(data)):
            dta[i] = data[i]
        err = self.handle.pipx40_setMaskPattern(self.vi, sub, dta)
        return err

    def GetMaskPattern(self, sub):
        # get size of subunit and create an array to hold the data
        e, t, rows, cols = self.SubInfo(self.vi, sub, 1)
        dwords = calc_dwords(rows * cols)
        dta = (c_uint32 * dwords)()
        err = self.handle.pipx40_getMaskPattern(self.vi, sub, byref(dta))

        # copy to python array
        data = array('L')
        i = 0
        while (i < dwords):
            data.append(dta[i])
            i = i + 1

        return err, data

    def GetMaskState(self, sub, bit):
        state = c_uint(0)
        err = self.handle.pipx40_getMaskState(self.vi, sub, bit, byref(state))
        return err, state.value

    def GetCrosspointMask(self, sub, row, column):
        state = c_uint(0)
        err = self.handle.pipx40_getCrosspointMask(self.vi, sub, row, column, byref(state))
        return err, state.value

    # Bit Operation - Write Functions
    def SetChannelState(self, sub, bit, action):
        err = self.handle.pipx40_setChannelState(self.vi, sub, bit, action)
        return err

    def SetCrosspointState(self, sub, row, column, action):
        err = self.handle.pipx40_setCrosspointState(self.vi, sub, row, column, action)
        return err

    def SetChannelPattern(self, sub, data):
        dta = (c_uint * len(data))()
        for i in range(len(data)):
            dta[i] = data[i]
        err = self.handle.pipx40_setChannelPattern(self.vi, sub, dta)
        return err

    def OperateSwitch(self, sub, func, seg, sw, act):
        state = c_uint(0)
        err = self.handle.pipx40_operateSwitch(self.vi, sub, func, seg, sw, act, byref(state))
        return err, state.value

    # Bit Operation - Read Functions
    def ReadInputState(self, sub, bit):
        state = c_uint(0)
        err = self.handle.pipx40_readInputState(self.vi, sub, bit, byref(state))
        return err, state.value

    def GetChannelState(self, sub, bit):
        state = c_uint(0)
        err = self.handle.pipx40_getChannelState(self.vi, sub, bit, byref(state))
        return err, state.value

    def ReadInputPattern(self, sub, data):
        # get size of subunit and create an array to hold the data
        e, t, rows, cols = self.SubInfo(self.vi, sub, 0)
        dwords = calc_dwords(rows * cols)
        dta = (c_uint32 * dwords)()

        err = self.handle.pipx40_ReadInputPattern(self.vi, sub, byref(dta))

        # copy to python array
        data = array('L')
        i = 0
        while (i < dwords):
            data.append(dta[i])
            i = i + 1

        return err, data

    def GetCrosspointState(self, sub, row, column):
        state = c_uint(0)
        err = self.handle.pipx40_getCrosspointState(self.vi, sub, row, column, byref(state))
        return err, state.value

    def GetChannelPattern(self, sub):
        # get size of subunit and create c_uint32 'array' to hold the data
        e, t, rows, cols = self.SubInfo(sub, 1)
        dwords = calc_dwords(rows * cols)
        dta = (c_uint32 * dwords)()

        # get the data
        err = self.handle.pipx40_getChannelPattern(self.vi, sub, byref(dta))

        # copy to python array
        data = array('L')
        i = 0
        while (i < dwords):
            data.append(dta[i])
            i = i + 1

        return err, data

    # Resistor Card specific

    def ReadCalibration(self, sub, index):
        data = c_uint(0)
        err = self.handle.pipx40_readCalibration(self.vi, sub, bit, byref(data))
        return err, data.value

    def WriteCalibration(self, sub, index, data):
        err = self.handle.pipx40_writeCalibration(self.vi, sub, index, data)
        return err

    def WriteCalibrationFP(self, sub, store, offset, numvals, data):
        d = (numvals * c_double)()

        for x in range(numvals):
            d[x] = data[x]

        err = self.handle.pipx40_writeCalibrationFP(self.vi, sub, store, offset, numVal, d)
        return err

    # 6 Nov 2019 - Alan Hume
    # Changed ReadCalibrationFP to return 'array' of calibration value
    def ReadCalibrationFP(self, sub, store, offset, numvals):
        d = (numvals * c_double)()
        data = array('d')
        err = self.handle.pipx40_readCalibrationFP(self.vi, sub, store, 0, numvals, byref(d))

        for x in range(numvals):
            data.append(d[x])

        return err, data

    # input subunit, store and required interval
    # sets card calibration data to todays date with defined interval
    def WriteCalibrationDate(self, sub, store, interval):
        err = self.handle.pipx40_writeCalibrationDate(self.vi, sub, store, interval)
        return err

    def ReadCalibrationDate(self, sub, store):
        year = c_uint(0)
        day = c_uint(0)
        interval = c_uint(0)
        err = self.handle.pipx40_readCalibrationDate(self.vi, sub, store, byref(year), byref(day), byref(interval))
        return err, year.value, day.value, interval.value

    def SetCalibrationPoint(self, sub, index):
        err = self.handle.pipx40_setCalibrationPoint(self.vi, sub, index)
        return err

    def ResSetResistance(self, sub, mode, value):
        res = c_double(value)
        err = self.handle.pipx40_resSetResistance(self.vi, sub, mode, res)
        return err

    def ResGetResistance(self, sub):
        res = c_double(0.0)
        err = self.handle.pipx40_resGetResistance(self.vi, sub, byref(res))
        return err, res.value

    def ResGetInfo(self, sub, ):
        minRes = c_double(0.0)
        maxRes = c_double(0.0)
        refRes = c_double(0.0)
        precPC = c_double(0.0)
        precDelta = c_double(0.0)
        int1 = c_double(0.0)
        intDelta = c_double(0.0)
        capabilities = c_uint(0)
        err = self.handle.pipx40_resGetInfo(self.vi, sub, byref(minRes), byref(maxRes), byref(refRes), byref(precPC),
                                            byref(precDelta), byref(int1), byref(intDelta), byref(capabilities))
        return err, minRes.value, maxRes.value, refRes.value, precPC.value, precDelta.value, int1.value, intDelta.value, capabilities.value

    # Attenuator card functions

    def AttenGetType(self, sub):
        strng = create_string_buffer(100)
        err = self.handle.pipx40_attenGetType(self.vi, sub, byref(strng))
        return err, str(strng.value.decode())

    def AttenGetInfo(self, sub):
        size = c_float(0.0)
        steps = c_uint(0)
        stype = c_uint(0)
        err = self.handle.pipx40_attenGetInfo(self.vi, sub, byref(stype), byref(steps), byref(size))
        return err, stype.value, steps.value, size.value

    def AttenSetAttenuation(self, sub, atten):
        err = self.handle.pipx40_attenSetAttenuation(self.vi, sub, atten)
        return err

    def AttenGetAttenuation(self, sub):
        atten = c_float(0.0)
        err = self.handle.pipx40_attenGetAttenuation(self.vi, sub, byref(atten))
        return err, atten.value

    def AttenGetPadValue(self, sub, pad):
        atten = c_float(0.0)
        err = self.handle.pipx40_attenGetPadValue(self.vi, sub, byref(atten))
        return err, atten.value

    # PSU card functions

    def PsuGetType(self, sub):
        strng = create_string_buffer(100)
        err = self.handle.pipx40_psuGetType(self.vi, sub, byref(strng), 100)
        return err, str(strng.value.decode())

    def PsuGetInfo(self, sub):
        stype = c_uint(0)
        volts = c_double(0.0)
        amps = c_double(0.0)
        precis = c_uint(0)
        capb = c_uint(0)
        err = self.handle.pipx40_psuGetInfo(self.vi, sub, byref(stype), byref(volts), byref(amps), byref(precis),
                                            byref(capb))
        return err, stype.value, volts.value, amps.value, precis.value, capb.value

    def PsuGetVoltage(self, sub):
        volts = c_double(0.0)
        err = self.handle.pipx40_psuGetVoltage(self.vi, sub, byref(volts))
        return err, volts.value

    def PsuSetVoltage(self, sub, v):
        volts = c_double(v)
        err = self.handle.pipx40_psuSetVoltage(self.vi, sub, volts)
        return err

    def PsuEnable(self, sub, enable):
        err = self.handle.pipx40_psuEnable(self.vi, sub, enable)
        return err

    # Battery Simulator Functions

    def BattSetVoltage(self, sub, v):
        volts = c_double(v)
        err = self.handle.pipx40_battSetVoltage(self.vi, sub, volts)
        return err

    def BattGetVoltage(self, sub):
        volts = c_double(0.0)
        err = self.handle.pipx40_battGetVoltage(self.vi, sub, byref(volts))
        return err, volts.value

    def BattSetCurrent(self, sub, curr):
        current = c_double(curr)
        err = self.handle.pipx40_battSetVoltage(self.vi, sub, current)
        return err

    def BattGetCurrent(self, sub):
        current = c_double(0.0)
        err = self.handle.pipx40_battGetCurrent(self.vi, sub, byref(current))
        return err, current.value

    def BattSetEnable(self, sub, pattern):
        err = self.handle.pipx40_battSetEnable(self.vi, sub, pattern)
        return err

    def BattGetEnable(self, sub):
        pattern = c_uint(0)
        err = self.handle.pipx40_battGetEnable(self.vi, sub, byref(pattern))
        return err, pattern.value

    def BattReadInterlockState(self, sub):
        state = c_uint(0)
        err = self.handle.pipx40_battReadInterlockState(self.vi, sub, byref(state))
        return err, state.value

    # Thermocouple Simulator functions

    def VSourceSetVoltage(self, sub, voltage):
        volts = c_double(voltage)
        err = self.handle.pipx40_vsourceSetVoltage(self.vi, sub, volts)
        return err

    def VSourceGetVoltage(self, sub):
        voltage = c_double(0.0)
        err = self.handle.pipx40_vsourceGetVoltage(self.vi, sub, byref(voltage))
        return err, voltage.value

    def VSourceSetRange(self, sub, ts_range):
        err = self.ERRORCODE["ERROR_BAD_RANGE"]
        isoutsub = 1
        if ts_range in self.TS_RANGE.values():
            tsrng = c_uint(ts_range)
            err = self.handle.pipx40_SetAttribute(self.vi, sub, isoutsub,
                self.ATTR["TS_SET_RANGE"], byref(tsrng))
        return err

    def VSourceGetRange(self, sub):
        err = self.ERRORCODE["ERROR_BAD_RANGE"]
        isoutsub = 1
        ts_range = c_uint(0)
        err = self.handle.pipx40_GetAttribute(self.vi, sub, isoutsub,
            self.ATTR["TS_SET_RANGE"], byref(ts_range))
        return err, ts_range.value

    def VSourceInfo(self, sub):
        is_output = c_uint32(1)

        low_range_min = c_double(0.0)
        low_range_med = c_double(0.0)
        low_range_max = c_double(0.0)
        low_range_max_dev = c_double(0.0)
        low_range_prec_pc = c_double(0.0)
        low_range_prec_delta = c_double(0.0)

        med_range_min = c_double(0.0)
        med_range_med = c_double(0.0)
        med_range_max = c_double(0.0)
        med_range_max_dev = c_double(0.0)
        med_range_prec_pc = c_double(0.0)
        med_range_prec_delta = c_double(0.0)

        high_range_min = c_double(0.0)
        high_range_med = c_double(0.0)
        high_range_max = c_double(0.0)
        high_range_max_dev = c_double(0.0)
        high_range_prec_pc = c_double(0.0)
        high_range_prec_delta = c_double(0.0)

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_LOW_RANGE_MIN"],
                                            byref(low_range_min)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_LOW_RANGE_MED"],
                                            byref(low_range_med)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_LOW_RANGE_MAX"],
                                            byref(low_range_max)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_LOW_RANGE_MAX_DEV"],
                                            byref(low_range_max_dev)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_LOW_RANGE_PREC_PC"],
                                            byref(low_range_prec_pc)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_LOW_RANGE_PREC_DELTA"],
                                            byref(low_range_prec_delta)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_MED_RANGE_MIN"],
                                            byref(med_range_min)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_MED_RANGE_MED"],
                                            byref(med_range_med)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_MED_RANGE_MAX"],
                                            byref(med_range_max)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_MED_RANGE_MAX_DEV"],
                                            byref(med_range_max_dev)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_MED_RANGE_PREC_PC"],
                                            byref(med_range_prec_pc)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_MED_RANGE_PREC_DELTA"],
                                            byref(med_range_prec_delta)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_HIGH_RANGE_MIN"],
                                            byref(high_range_min)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_HIGH_RANGE_MED"],
                                            byref(high_range_med)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_HIGH_RANGE_MAX"],
                                            byref(high_range_max)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_HIGH_RANGE_MAX_DEV"],
                                            byref(high_range_max_dev)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_HIGH_RANGE_PREC_PC"],
                                            byref(high_range_prec_pc)
        )

        err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                            is_output,
                                            self.ATTR["TS_HIGH_RANGE_PREC_DELTA"],
                                            byref(high_range_prec_delta)
        )

        return err, low_range_min.value, \
            low_range_med.value, \
            low_range_max.value, \
            low_range_max_dev.value, \
            low_range_prec_pc.value, \
            low_range_prec_delta.value, \
            med_range_min.value, \
            med_range_med.value, \
            med_range_max.value, \
            med_range_max_dev.value, \
            med_range_prec_pc.value, \
            med_range_prec_delta.value, \
            high_range_min.value, \
            high_range_med.value, \
            high_range_max.value, \
            high_range_max_dev.value, \
            high_range_prec_pc.value, \
            high_range_prec_delta.value

    def VSourceGetTemperature(self, unit):
        err = self.ERRORCODE["ERROR_BAD_ATTR_CODE"]
        is_output = 1
        sub = 1
        temperatures = (c_double * 4)(0.0, 0.0, 0.0, 0.0)
        if unit == self.ATTR["TS_TEMPERATURES_C"] or unit == self.ATTR["TS_TEMPERATURES_F"]:
            err = self.handle.pipx40_GetAttribute(self.vi, sub,
                                               is_output,
                                               unit,
                                               byref(temperatures)
                                               )
        return err, [temp for temp in temperatures]

    def SetAttribute(self, sub, io, attrib, value):
        val = c_uint(value)
        err = self.handle.pipx40_SetAttribute(self.vi, sub, io, attrib, byref(val))
        return err

    def GetAttribute(self, sub, io, attrib):
        val = c_uint(0)
        err = self.handle.pipx40_GetAttribute(self.vi, sub, io, attrib, byref(val))
        return err, val.value

    def CleanUp(self):
        err = self.handle.pipx40_cleanUp()
        return err

    ### Deprecated Thermocouple Functions ###

    # def VSourceSetEnable(self, sub, pattern):
    #     patt = c_uint(pattern)
    #     err = self.handle.pipx40_vsourceSetEnable(self.vi, sub, patt)
    #     return err
    #
    # def VSourceGetEnable(self, sub):
    #     err = self.handle.pipx40_vsourceGetEnable(self.vi, sub, byref(patt))
    #     return err, patt.value

### Deprecated attribute definitions kept for backwards compatibility

ERROR_BASE				    = 0xBFFC0800			# 3220965376
ERROR_BAD_SESSION	        = (ERROR_BASE + 0x00)	# Not a valid pipx40 session
ERROR_NO_INFO			    = (ERROR_BASE + 0x01)	# Card information unobtainable - hardware problem
ERROR_CARD_DISABLED		    = (ERROR_BASE + 0x02)	# Card disabled - hardware problem
ERROR_BAD_SUB			    = (ERROR_BASE + 0x03)	# Card has no sub-unit with specified number
ERROR_BAD_CHANNEL		    = (ERROR_BASE + 0x04)	# Sub-unit has no channel with specified number
ERROR_NO_CAL_DATA		    = (ERROR_BASE + 0x05)	# Sub-unit has no calibration data to write/read
ERROR_BAD_ARRAY			    = (ERROR_BASE + 0x06)	# Array type, size or shape is incorrect
ERROR_MUX_ILLEGAL		    = (ERROR_BASE + 0x07)	# Non-zero write data is illegal for MUX sub-unit
ERROR_EXCESS_CLOSURE	    = (ERROR_BASE + 0x08)	# Sub-unit closure limit exceeded
ERROR_ILLEGAL_MASK		    = (ERROR_BASE + 0x09)	# One or more of the specified channels cannot be masked
ERROR_OUTPUT_MASKED		    = (ERROR_BASE + 0x0A)	# Cannot activate an output that is masked
ERROR_FAILED_INIT		    = (ERROR_BASE + 0x0B)	# Cannot open a Pickering card with this resource name
ERROR_READ_FAIL			    = (ERROR_BASE + 0x0C)	# Failed read from hardware
ERROR_WRITE_FAIL		    = (ERROR_BASE + 0x0D)	# Failed write to hardware
ERROR_VISA_OP			    = (ERROR_BASE + 0x0E)	# VISA operation failed
ERROR_VISA_VERSION		    = (ERROR_BASE + 0x0F)	# Incompatible VISA version
ERROR_SUB_TYPE			    = (ERROR_BASE + 0x10)	# Function call incompatible with sub-unit type or capabilities
ERROR_BAD_ROW			    = (ERROR_BASE + 0x11)	# Matrix row value out of range
ERROR_BAD_COLUMN		    = (ERROR_BASE + 0x12)	# Matrix column value out of range
ERROR_BAD_ATTEN			    = (ERROR_BASE + 0x13)	# Attenuation value out of range
ERROR_BAD_VOLTAGE		    = (ERROR_BASE + 0x14)	# Voltage value out of range
ERROR_BAD_CAL_INDEX		    = (ERROR_BASE + 0x15)	# Calibration reference out of range
ERROR_BAD_SEGMENT		    = (ERROR_BASE + 0x16)	# Segment number out of range
ERROR_BAD_FUNC_CODE		    = (ERROR_BASE + 0x17)	# Function code value out of range
ERROR_BAD_SUBSWITCH		    = (ERROR_BASE + 0x18)	# Subswitch value out of range
ERROR_BAD_ACTION		    = (ERROR_BASE + 0x19)	# Action code out of range
ERROR_STATE_CORRUPT		    = (ERROR_BASE + 0x1A)	# Cannot execute due to corrupt sub-unit state
ERROR_BAD_ATTR_CODE		    = (ERROR_BASE + 0x1B)	# Unrecognised attribute code
ERROR_EEPROM_WRITE_TMO	    = (ERROR_BASE + 0x1C)	# Timeout writing to EEPROM
ERROR_ILLEGAL_OP		    = (ERROR_BASE + 0x1D)	# Operation is illegal in the sub-unit's current state
ERROR_BAD_POT			    = (ERROR_BASE + 0x1E)	# Unrecognised pot number requested
ERROR_MATRIXR_ILLEGAL	    = (ERROR_BASE + 0x1F)	# Invalid write pattern for MATRIXR sub-unit
ERROR_MISSING_CHANNEL	    = (ERROR_BASE + 0x20)	# Attempted operation on non-existent channel
ERROR_CARD_INACCESSIBLE	    = (ERROR_BASE + 0x21)	# Card cannot be accessed (failed/removed/unpowered)
ERROR_BAD_FP_FORMAT		    = (ERROR_BASE + 0x22)	# Unsupported internal floating-point format (internal error)
ERROR_UNCALIBRATED		    = (ERROR_BASE + 0x23)	# Sub-unit is not calibrated
ERROR_BAD_RESISTANCE	    = (ERROR_BASE + 0x24)	# Unobtainable resistance value
ERROR_BAD_STORE			    = (ERROR_BASE + 0x25)	# Invalid calibration store number
ERROR_BAD_MODE			    = (ERROR_BASE + 0x26)	# Invalid mode value
ERROR_SETTINGS_CONFLICT	    = (ERROR_BASE + 0x27)	# Conflicting device settings
ERROR_CARD_TYPE			    = (ERROR_BASE + 0x28)	# Function call incompatible with card type or capabilities
ERROR_BAD_POLE			    = (ERROR_BASE + 0x29)	# Switch pole value out of range
ERROR_MISSING_CAPABILITY	= (ERROR_BASE + 0x2A)	# Attempted to activate a non-existent capability
ERROR_MISSING_HARDWARE	    = (ERROR_BASE + 0x2B)	# Action requires hardware that is not present
ERROR_HARDWARE_FAULT	    = (ERROR_BASE + 0x2C)	# Faulty hardware
ERROR_EXECUTION_FAIL	    = (ERROR_BASE + 0x2D)	# Failed to execute (e.g. blocked by a hardware condition)
ERROR_BAD_CURRENT		    = (ERROR_BASE + 0x2E)	# Current value out of range
ERROR_BAD_RANGE			    = (ERROR_BASE + 0x2F)	# Invalid range value
ERROR_ATTR_UNSUPPORTED	    = (ERROR_BASE + 0x30)	# Attribute not supported
ERROR_BAD_REGISTER		    = (ERROR_BASE + 0x31)	# Register number out of range
ERROR_MATRIXP_ILLEGAL	    = (ERROR_BASE + 0x32)	# Invalid channel closure or write pattern for MATRIXP sub-unit
ERROR_BUFFER_UNDERSIZE	    = (ERROR_BASE + 0x33)	# Data buffer too small
ERROR_ACCESS_MODE		    = (ERROR_BASE + 0x34)	# Inconsistent shared access mode
ERROR_POOR_RESISTANCE	    = (ERROR_BASE + 0x35)	# Resistance outside limits
ERROR_BAD_ATTR_VALUE 	    = (ERROR_BASE + 0x36)	# Bad attribute value
ERROR_INVALID_POINTER 	    = (ERROR_BASE + 0x37)	# Invalid pointer
ERROR_ATTR_READ_ONLY 	    = (ERROR_BASE + 0x38)	# Attribute is read only
ERROR_ATTR_DISABLED 	    = (ERROR_BASE + 0x39)	# Attribute is disabled
ERROR_PSU_MAIN_DISABLED	    = (ERROR_BASE + 0x3A)	# Main output is disabled, cannot enable the channel
ERROR_OUT_OF_MEMORY_HEAP	= (ERROR_BASE + 0x3B)   # Unable to allocate memory on Heap
ERROR_INVALID_PROCESSID     = (ERROR_BASE + 0x3C)   # Invalid ProcessID
ERROR_SHARED_MEMORY         = (ERROR_BASE + 0x3D)   # Shared memory error
ERROR_CARD_OPENED_OTHER_PROCESS = (ERROR_BASE + 0x3E) # Card is opened by a process in exclusive mode

ERROR_UNKNOWN			    = (ERROR_BASE + 0x7FF)	# Unknown error code


STAT_NO_CARD		        = 0x80000000	# No Pickering card open on the session
STAT_WRONG_DRIVER	        = 0x40000000	# Card requires later driver version
STAT_EEPROM_ERR		        = 0x20000000	# Error interpreting card EEPROM data
STAT_DISABLED		        = 0x10000000	# Card is disabled
STAT_NO_SUB			        = 0x08000000	# Card has no sub-unit with specified number
STAT_BUSY			        = 0x04000000	# Busy (card or sub-unit)
STAT_HW_FAULT		        = 0x02000000	# Hardware fault (eg. defective serial loop)
STAT_PARITY_ERROR	        = 0x01000000	# PCIbus parity error
STAT_PSU_INHIBITED	        = 0x00800000	# PSU sub-unit - supply is disabled (by software)
STAT_PSU_SHUTDOWN	        = 0x00400000	# PSU sub-unit - supply is shutdown (due to overload)
STAT_PSU_CURRENT_LIMIT	    = 0x00200000	# PSU sub-unit - supply is operating in current-limited mode
STAT_CORRUPTED		        = 0x00100000	# Sub-unit logical state is corrupted
STAT_CARD_INACCESSIBLE	    = 0x00080000	# Card cannot be accessed (failed/removed/unpowered)
STAT_UNCALIBRATED	        = 0x00040000	# Calibration data is faulty (card or sub-unit)
STAT_CALIBRATION_DUE        = 0x00020000	# Calibration is due (card or sub-unit)
STAT_BIRST_ENABLED	        = 0x00010000	# BIRST is active (card or sub-unit)
STAT_OK				        = 0x00000000

TYPE_SW		        = 1	    # Uncommitted switches
TYPE_MUX	        = 2	    # Relay multiplexer (single-channel only)
TYPE_MUXM	        = 3	    # Relay multiplexer (multi-channel capable)
TYPE_MAT	        = 4	    # Standard matrix
TYPE_MATR	        = 5	    # RF matrix
TYPE_DIG	        = 6	    # Digital outputs
TYPE_RES	        = 7	    # Programmable Resistor
TYPE_ATTEN	        = 8	    # Programmable Attenuator
TYPE_PSUDC	        = 9	    # Power supply - DC
TYPE_BATT	        = 10	# Battery simulator
TYPE_VSOURCE	    = 11	# Programmable voltage source
TYPE_MATP	        = 12	# Matrix with restricted operating modes
TYPE_MUXMS	        = 13	# Relay multiplexer (MUXM hardware emulated as MUX)
TYPE_FI		        = 14	# Fault insertion sub-unit
TYPE_LVDT	        = 15	# LVDT simulator

CAL_STORE_USER		= 0
CAL_STORE_FACTORY	= 1

TS_AUTO_RANGE       = 0
TS_LOW_RANGE        = 1
TS_MED_RANGE        = 2
TS_HIGH_RANGE       = 3


ATTR_TYPE							= 0x400	# Gets/Sets DWORD attribute value of Type of the Sub-unit (values: TYPE_MUXM, TYPE_MUXMS)
ATTR_MODE							= 0x401	# Gets/Sets DWORD attribute value of Mode of the Card

# Current monitoring attributes
ATTR_CNFGREG_VAL					= 0x402	# Gets/Sets WORD value of config register
ATTR_SHVLREG_VAL 					= 0x403	# Gets WORD value of shuntvoltage register
ATTR_CURRENT_VAL 					= 0x404	# Gets double current value in Amps

# Read-only Power Supply attributes
ATTR_INTERLOCK_STATUS				= 0x405	# Gets BOOL value of interlock status
ATTR_OVERCURRENT_STATUS_MAIN		= 0x406	# Gets BOOL value of main overcurrent status
ATTR_OVERCURRENT_STATUS_CH			= 0x407	# Gets BOOL value of overcurrent status on specific channel

# Read/Write Power Supply attributes
ATTR_OUTPUT_ENABLE_MAIN				= 0x408	# Gets/Sets BOOL value. Enables/Disables main
ATTR_OUTPUT_ENABLE_CH				= 0x409	# Gets/Sets BOOL value. Enables/Disables specific channel

# Read/Write Thermocouple Simulator functions
ATTR_TS_SET_RANGE					= 0x40A	# Gets/Sets Auto range which toggles between based on the value
# Read-only function
ATTR_TS_LOW_RANGE_MIN				= 0x40B
ATTR_TS_LOW_RANGE_MED				= 0x40C
ATTR_TS_LOW_RANGE_MAX				= 0x40D
ATTR_TS_LOW_RANGE_MAX_DEV			= 0x40E
ATTR_TS_LOW_RANGE_PREC_PC			= 0x40F
ATTR_TS_LOW_RANGE_PREC_DELTA		= 0x410
ATTR_TS_MED_RANGE_MIN				= 0x411
ATTR_TS_MED_RANGE_MED				= 0x412
ATTR_TS_MED_RANGE_MAX				= 0x413
ATTR_TS_MED_RANGE_MAX_DEV			= 0x414
ATTR_TS_MED_RANGE_PREC_PC			= 0x415
ATTR_TS_MED_RANGE_PREC_DELTA		= 0x416
ATTR_TS_HIGH_RANGE_MIN				= 0x417
ATTR_TS_HIGH_RANGE_MED				= 0x418
ATTR_TS_HIGH_RANGE_MAX				= 0x419
ATTR_TS_HIGH_RANGE_MAX_DEV			= 0x41A
ATTR_TS_HIGH_RANGE_PREC_PC			= 0x41B
ATTR_TS_HIGH_RANGE_PREC_DELTA		= 0x41C
ATTR_TS_POT_VAL						= 0x41D # Read Pot Value from user store

# Write-only function
ATTR_TS_SET_POT						= 0x41E
ATTR_TS_SAVE_POT					= 0x41F
ATTR_TS_DATA_DUMP					= 0x420
ATTR_MUXM_MBB						= 0x421

# Read/Write LVDT functions
# LVDT Mk2 Set only
ATTR_LVDT_RESET						= 0x422
ATTR_LVDT_CHANNEL_AUTO_PHASE		= 0x423
ATTR_LVDT_AUTO_INPUT_ATTEN			= 0x424
ATTR_LVDT_CHANNEL_INVERT			= 0x439
ATTR_LVDT_PHASE_TRACKING			= 0x43A
ATTR_LVDT_PERIOD_COUNTS				= 0x43B
ATTR_LVDT_SAMPLE_LOAD				= 0x43C

# LVDT Mk2 Set/Get
ATTR_LVDT_CHANNEL_POSITION			= 0x425
ATTR_LVDT_CHANNEL_MODE2_POSITION	= 0x426
ATTR_LVDT_CHANNEL_PERCENT_POSITION	= 0x427
ATTR_LVDT_CHANNEL_MODE2_PERCENT_POSITION	= 0x428
ATTR_LVDT_CHANNEL_VOLTAGE_SUM		= 0x429
ATTR_LVDT_CHANNEL_VOLTAGE_DIFF		= 0x42A
ATTR_LVDT_CHANNEL_OUT_GAIN			= 0x42B
ATTR_LVDT_MANUAL_INPUT_ATTEN		= 0x42C
ATTR_LVDT_CHANNEL_MODE				= 0x42D
ATTR_LVDT_CHANNEL_DELAY				= 0x432
ATTR_LVDT_CHANNEL_MODE2_DELAY		= 0x433
ATTR_LVDT_CHANNEL_OUT_LEVEL			= 0x437
ATTR_LVDT_CHANNEL_INPUT_LEVEL		= 0x434

# LVDT Mk2 Get only
ATTR_LVDT_CHANNEL_INPUT_FREQ		= 0x435
ATTR_LVDT_CALIBRATION_VALUES		= 0x436
ATTR_LVDT_DSPIC_VERSION				= 0x438

ATTR_TS_TEMPERATURES_C				= 0x42E  # Read 7 sensors on 1192r0 41-760 I2C Compensation Block in degrees Celsius
ATTR_TS_TEMPERATURES_F				= 0x42F  # Read 7 sensors on 1192r0 41-760 I2C Compensation Block in degrees Farenheit
ATTR_TS_EEPROM						= 0x430  # Read/write 34LC02 eeprom
ATTR_TS_EEPROM_OFFSET               = 0x431  # Supply offset to eeprom

VSOURCE_ALL_VSOURCE_SUB_UNITS       = 0
