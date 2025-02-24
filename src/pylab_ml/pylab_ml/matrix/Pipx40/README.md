# Python Pipx40 #

Python Pipx40 is a Python wrapper for Pickering Pipx40 VISA driver. It supports both Python 2.x and 3.x and has one python dependency (`pyvisa`). 

----------
# Changelog #

> - 1.3 - Updates thermocouple functions, adds error/status/attribute code dicts, adds VSourceInfo(), VSourceGetTemperature(), 
>Updated example code and readme with Python 2.x/3.x compatibility improvements. Functions return native strings in both Python 2.x and 3.x.
>string `decode()` workaround no longer necessary in Python 3.
> - 1.2 - Added functions for Thermocouple, error/status codes etc, and modified a few other functions
> - 1.1 - Refactor for use with pip installer and adds 64 bit support
> - 1.0 - Initial Release

----------
# Installation instructions #

We provide both a python module that can be installed to the system using `pip` and can be added manually to a project by copying a file into the directory that you are working in. For either installation method please make sure that you have installed Pickering PXI Installer Package in the default VXIPNP mode, which also requires NI VISA to be installed. These can be found at the following addresses:

 - [PXI Installer Package](http://pickeringtest.info/downloads/drivers/PXI_Drivers/)
 - [NI VISA](http://www.ni.com/visa/)

----------
## Install Using `pip` ##

To install Python Pipx40 using pip open a command line prompt and navigate to the directory the driver has been extracted to. From there enter the following command:
```
pip install .\
```
This should install both Python Pipx40 and the `pyvisa`.

----------
## Install Manually ##

To install Python Pipx40 manually please copy `Pipx40.py` from the extracted directory to your working directory. You will also need to make sure that `pyvisa` is installed which can be done with either:
`pip install pyvisa` with an internet connection or from the `pyvisa` directory inside the extracted directory `pip install .` 

----------
# Using Pipx40 # 

## List Cards ## 

To get a list of available cards use `pipx40base.FindFreeCards()`. This will return a list of resource strings that
can be used to open cards. `pipx40base.CountFreeCards()` can be used to return the number of cards available for use.
Please see below for examples on how to use both these functions: 

```python 
from Pipx40 import *

#Initialising Base Class
base = pipx40_base()

# Return the number of available cards
count = base.CountFreeCards()

print("Found", count, "free cards.")

# Return a list of free cards
list = base.FindFreeCards()

for index, card in enumerate(list):
    print("Card", index + 1, ":", card) 
```

## Opening/Closing Cards ## 

Cards can be opened using a resource string, which can be found from FindFreeCards() or from the Pickering 
General Soft front Panel. The following example code will open a card with a specified resource string, 
query its ID, and close it:

```python

resourceString = "PXI21::1::INSTR"

# Open card using resource string
card = pipx40_card(resourceString, 0 ,0)

# Returns an error code and cardID string containing model name, serial number and firmware revision
error, cardId = card.GetCardId()

print(cardId)

# Close the card
card.Close()
```

## Error Handling ## 

Most functions in the Pipx40 library return an error code. Error codes are a numerical 
value indicating an error condition. The `ErrorMessage()` function can be used to return a more useful 
string description of a given error code as in the example below: 

```python
# Check for errors, ideally after every function call:
if error:
    # This function will take an error code and return a string description of the error
    error, errorString = card.ErrorMessage(error)
    print("Error: ", errorString)
```

## Operate Switching Cards ## 

There are three main types of switching cards:
 - Switches
 - Multiplexer
 - Matrix

To operate Switches and Multiplexers use `SetChannelState()` providing subunit, switch point, and switch state. 
Matrices can be controller using `SetCrosspointState()` which requires the subunit, row, column, and switch state. 
Please see below for worked examples on using these functions:

```python
# Control Switches and Multiplexer cards:
subunit = 1 
switchpoint = 1

error = card.SetChannelState(subunit, switchpoint, 1)
if error:
    error, errorString = card.ErrorMessage(error)
    print("Error: ", errorString)

# Control Matrix cards:
x = 1 
y = 1 

error = card.SetCrosspointState(subunit, x, y, 1)
if error:
    error, errorString = card.ErrorMessage(error)
    print("Error: ", errorString)
```

## Operate Resistor Cards ## 

Resistor cards come in two varieties: Programmable Resistor, and Precision Resistor. Programmable Resistors are 
controlled like Switch Cards shown above. Precision Resistor Cards have specific resistor functions. 
To set a resistance `ResSetResistance` is used and to get the current resistance `ResGetResistance` is used, 
as shown below:

```python 
# Set Resistance of given subunit:
mode = 0
resistance = 330.0

error = card.ResSetResistance(subunit, mode, resistance)
if error:
    error, errorString = card.ErrorMessage(error)
    print("Error: ", errorString)

# Retrieve current resistance of a given subunit:
error, resistance = card.ResGetResistance(subunit) 
if error:
    error, errorString = card.ErrorMessage(error)
    print("Error: ", errorString)
print("Resistance:", resistance)

```

## Operate Attenuator Cards ##

Attenuators have specific functions for controlling them. To set attenuation use `AttenSetAttenuation()` providing the 
subunit and attenuation expressed in decibels. To retrieve the current attenuation use `AttenGetAttenuation()` giving the 
subunit. It returns an error code and the attenuation expressed in decibels. Please see below for worked examples on 
how to use these functions:

```python 
# Setting attenuation:
attenuation = 1.5   # Value in decibels (dB)

error = card.AttenSetAttenuation(subunit, c_float(attenuation)) 

# Retrieving attentuation: 
error = card.AttenGetAttenuation(subunit) 

print("Attenuation (dB):", attenuation)
```

## Operate Battery Simulator Cards ## 

Battery Simulators have specific functions for controlling them. To set voltage use `BattSetVoltage()` providing the 
subunit and voltage. To retrieve the voltage use `BattGetVoltage()` giving the subunit. To set current use `BattSetcurrent()` 
providing the subunit and current. To retrieve the current use `BattGetcurrent()` giving the subunit. It returns an error 
code and set current. To enable output use `BattSetEnable()` providing the subunit and the state to be set. 
To retrieve the present output state use `BattGetEnable()`. It returns an error code and the state. 
Please see below for worked examples on how to use these functions:

```python 
volts = 3.3 
current = 0.5

# Set Voltage
error = card.BattSetVoltage(subunit, volts)

# Set Current 
error = card.BattSetCurrent(subunit, current)

# Enable Output
error = card.BattSetEnable(subunit, 1)

# Get Voltage 
error, volts = card.BattGetVoltage(subunit)

# Get Current 
error, current = card.BattGetCurrent(subunit)

# Get Output State
error, state = card.BattGetEnable(subunit)
```

## Operate Thermocouple Simulator Cards ##

Thermocouple Simulators have specific functions for controlling them. To set the range use `VSourceSetRange()` 
providing the subunit and the range. It returns an error code. To retrieve the range use `VSourceGetRange()` 
providing the subunit. It returns an error code followed by the range. To set the voltage use `VSourceSetVoltage()` 
providing the subunit and the voltage in millivolts. It returns an error code. To retrieve the voltage use 
`VSourceGetVoltage()` providing the subunit. It returns an error code followed by the voltage in millivolts. 
To enable or disable outputs use `SetChannelState()` providing the subunit, bit number for the channel isolations, and the 
state that should be set. To retrieve the state of the outputs use `GetChannelState()` providing the subunit and bit number 
for the channel isolations. It returns an error code and the state if the requsted bit. Please refer to the product 
manual for more information on what subunit and bits to operate. To retrieve temperature readings from a connected 
thermocouple compensation block use `VSourceGetTemperature()` providing either `card.ATTR["TS_TEMPERATURES_C"]` 
or `card.ATTR["TS_TEMPERATURES_F"]` for temperature unit. It will return an error code and list of four 
temperatures. Please see below for worked examples on how to use these functions:

```python 
 # Set subunit voltage range to auto
range = card.TS_RANGE["AUTO"]
error = card.VSourceSetRange(subunit, range)

# Get voltage range of a subunit
error, range = card.VSourceGetRange(subunit)

# Set voltage to 19.5 mV on the subunit
mvolts = 19.5
error = card.VsourceSetVoltage(subunit, mvolts)

# Read the voltage of a subunit
error, mvolts = card.VSourceGetVoltage(subunit)

# Set isolation switches (Example for 41-760-001)
isolation_subunit = 33 

error = card.SetChannelState(isolation_subunit, 1, 1) # Turn Vo1 on
error = card.SetChannelState(isolation_subunit, 2, 1) # Turn Vcold1 on
error = card.SetChannelState(isolation_subunit, 1, 0) # Turn Vo1 off
error = card.SetChannelState(isolation_subunit, 2, 0) # Turn Vcold1 off

# Get compensation block temperatures
error, temperatures = card.VSourceGetTemperature(card.ATTR["TS_TEMPERATURES_C"])

index = 0
for index, temperature in enumerate(temperatures):
    print("Compensation block temperature ", index, ": ", temperature, "C")
```