"""
This module provides the ability to remotely control Array 364x programmable 
power supplies

These power supplies are rebadged under many names, so this module should work with
    - Array 3644A, 3645A and 3646A
    - Circuit Specialist 3644A, 3645A and 3646A
    - 3com 364x
"""

__version__    = "0.1"
__author__     = "Benoit Frigon"
__license__    = "GPL"
__copyright__  = "Licensed under the GPL license"
__email__      = "benoit@frigon.info"


#=========================================================================================
import os, sys
import serial
import re
import warnings
import struct


#=========================================================================================
class Psu:
    """
    Implements the remote control protocol of 364x series PSU
    """
    
    #----------------------------------------------------------------------------
    # Commands ID
    #----------------------------------------------------------------------------
    COMMAND_CHECK = 0x12
    COMMAND_SET = 0x80
    COMMAND_READ = 0x81
    COMMAND_CONTROLSTATE = 0x82
    COMMAND_READINFO = 0x8C 
    
    
    #----------------------------------------------------------------------------
    # Result codes
    #----------------------------------------------------------------------------
    RESULT_OK = 0x80
    RESULT_ERROR = 0x90
    
    
    #----------------------------------------------------------------------------
    def __init__(self, port=None, address=1, baudrate=38400, debug=False):
        """
        The port is immediately opened on object creation, when a port is given. It is not 
        opened when port is None and a successive call to open() will be needed
        
        Keyword arguments:
            - port : Serial port to use
            - address : Address of the PSU (0-254, default: 1)
            - baud : Baud rate (default: 38400)
            - debug : If True, print command and response frame data
            
        """    
        self.sio = serial.Serial(timeout=2)
        self.port = port
        self.baudrate = baudrate
        self.debug = debug
        
        self.address = 0
        self.remote = False
        
        
        if port is not None:
            self.open()
    
    
    #----------------------------------------------------------------------------
    def open(self):
        """
        Open the serial port and test the communication with the PSU
        
        Keyword arguments:
            None
            
        Return: 
            True if successful, False otherwise
        
        Raise:
            - SerialException : In case the device can not be found or can not be configured.
            - ValueError : Will be raised when parameter are out of range, e.g. baud rate, 
        """
        
        self.sio.port = self.port
        self.sio.baudrate = self.baudrate
        
        self.sio.open()
        self.sio.flushInput()
        
        return self.getInfo() is not None
    
    
    #----------------------------------------------------------------------------
    def close(self):
        """
        Disable the remote control on the PSU and close the serial port
        
        Keyword arguments: 
            None
        
        Return: 
            Nothing
        """
        
        self.disableRemoteControl()
        
        self.sio.close()
    
    
    #----------------------------------------------------------------------------
    def send(self, command, parameters=None):
        """
        Send a command frame to the PSU.
        
        Keyword arguments:
            - command : Command ID
            - parameters : Parameters to send 
            
        Return: 
            Response frame from the PSU or None if unsuccessful.
            
        Raise:
            SerialException : In case the function is called before the serial port was opened
            UnexpectedResponse : In case an Unexpected response or no response was received 
                                 from the psu364X
            InvalidParameter : In case the parameters is not valid object
        """
        
        if self.sio is None or not self.sio.isOpen():
            raise serial.SerialException("Serial port was not opened!")
        
        if parameters is None:
            parameters = ""
            
        if isinstance(parameters, (list, tuple)):
            if any(not isinstance(c, int) for c in parameters):
                raise ValueError("lists used as the parameters argument must only contain integers")
            
            if any((c < 0 or c > 255) for c in parameters):
                raise ValueError("lists used as the parameters argument must only contain integers representation of characters (0-255)")
            
            parameters = "".join(chr(c) for c in parameters)
            
        if type(parameters) is not str:
            raise ValueError("The parameters argument must be a string, a list or a tuple object")

        ## Build the command frame (26 bytes) => {0xAA}, {ADDRESS}, {COMMAND}, {DATA : 22 bytes}
        data = struct.pack('<B B B 22s', 0xAA, self.address, command, parameters)

        ## Append the checksum of the 25 first bytes to the frame ##
        data += chr((sum(ord(c) for c in data)) % 256)
        
        if self.debug:
            print "Send   :  ADDRESS={0} CMD={1:02X}".format(self.address, command)
            print "Frame  : ", " ".join("{:02X}".format(ord(c)) for c in data)
        
        ## Send the command frame ##
        self.sio.write(data)
        self.sio.flush()
        
        ## Read the response frame. It must be 26 bytes long ##
        result = self.sio.read(26)
        if self.debug:
            print "Return : ", " ".join("{:02X}".format(ord(c)) for c in result)
        
        
        if len(result) < 26:
            if self.debug: print "Result :  ERROR! Unexpected response length\n"
            raise UnexpectedResponse("Unexpected number of bytes")
        
        if not ord(result[25]) == (sum(ord(c) for c in result[:25])) % 256:
            if self.debug: print "Result :  ERROR! Bad checksum\n"
            raise UnexpectedResponse("Checksum failed")
        
        
        if (ord(result[2]) == self.COMMAND_CHECK and ord(result[3]) == self.RESULT_OK) or ord(result[2]) == command:
            if self.debug: print "Result :  OK\n"
        else:
            if self.debug: print "Result :  ERROR!\n"
            return None
        
        
        return result
    
    
    #----------------------------------------------------------------------------
    def getParameters(self):
        """
        Read the operating parameters of the PSU.
        
        Keyword arguments: 
            None
        
        Return: psu364x.Params object containing the operating parameters or None
                if unsuccessful.
        """
        
        data = self.send(self.COMMAND_READ)
        if data is None:
            return None
        
        params = Params()
        params.measureCurrent = float(struct.unpack_from('<H', data, 3)[0]) / 1000
        params.measureVoltage = float(struct.unpack_from('<L', data, 5)[0]) / 1000
        params.measurePower = float(struct.unpack_from('<H', data, 9)[0]) / 100
        params.maxCurrent = float(struct.unpack_from('<H', data, 11)[0]) / 1000
        params.maxVoltage = float(struct.unpack_from('<L', data, 13)[0]) / 1000
        params.maxPower = float(struct.unpack_from('<H', data, 17)[0]) / 100
        params.voltageSet = float(struct.unpack_from('<L', data, 19)[0]) / 1000
        
        
        params.outputState = (ord(data[23]) & 0x01 == 0x01)
        params.excessiveCurrent = (ord(data[23]) & 0x02 == 0x02)
        params.excessivePower = (ord(data[23]) & 0x04 == 0x04)
        
        return params
    
    
    #----------------------------------------------------------------------------
    def setParameters(self, params):
        """
        Set the operating parameters of the PSU.
        
        Keyword arguments:
            - params : psu364x.Params object containing the operating parameters.
        
        Return:
            True if successful, False otherwise
        """
        
        if not self.remote:
            warnings.warn("The PSU needs to be in remote control mode (PC) to set operating parameters.")
        
        data = struct.pack('<HIHIB',
            int(params.maxCurrent * 1000),      ## unsigned word, offset: 0
            int(params.maxVoltage * 1000),      ## unsigned long, offset: 2
            int(params.maxPower * 100),         ## unsigned word, offset: 6
            int(params.voltageSet * 1000),      ## unsigned long, offset: 8
            self.address                        ## unsigned byte, offset: 12
        )

        return self.send(self.COMMAND_SET, data) is not None
    
    
    #----------------------------------------------------------------------------
    def measureVoltage(self):
        """
        Read the actual voltage at the output
        
        Keyword arguments:
            None
        
        Return:
            Voltage reading (V), -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.measureVoltage
    
    
    #----------------------------------------------------------------------------
    def measurePower(self):
        """
        Read the actual output power
        
        Keyword arguments:
            None
        
        Return:       
            Watts reading (W), -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.measurePower
    
    
    #----------------------------------------------------------------------------
    def measureCurrent(self):
        """
        Read the actual output current
        
        Keyword arguments:
            None
        
        Return:
            Amps reading (A), -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.measureCurrent
    
    
    #----------------------------------------------------------------------------
    def getVoltage(self):
        """
        Get the current set voltage
        
        Keyword arguments:
            None
        
        Return:
            Voltage (V), -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.voltageSet
    
    
    #----------------------------------------------------------------------------
    def setVoltage(self, value):
        """
        Set the current set voltage
        
        Keyword arguments:
            - value : Voltage (V)
        
        Return:
            True if successful, False otherwise
        """
        
        params = self.getParameters()
        if params is None:
            return False
        
        params.voltageSet = value
        
        return self.setParameters(params)
    
    
    #----------------------------------------------------------------------------
    def getMaxVoltage(self):
        """
        Get the maximum voltage parameter
        
        Keyword arguments:
            None
        
        Return:
            Maximum voltage (V) parameter, -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.maxVoltage
    
    
    #----------------------------------------------------------------------------
    def setMaxVoltage(self, value):
        """
        Set the maximum voltage parameter
        
        Keyword arguments:
            - value : Maximum voltage (V)
        
        Return:
            True if successful, False otherwise
        """
        
        params = self.getParameters()
        if params is None:
            return False
        
        params.maxVoltage = value
        
        return self.setParameters(params)
    
    
    #----------------------------------------------------------------------------
    def getMaxCurrent(self):
        """
        Get the maximum curent parameter
        
        Keyword arguments:
            None
        
        Return:
            Maximum current (A) parameter. -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.maxCurrent
    
    
    #----------------------------------------------------------------------------
    def setMaxCurrent(self, value):
        """
        Set the maximum current paramter
        
        Keyword arguments:
            - value : Current (A)
        
        Return:
            True if successful, False otherwise
        """
        
        params = self.getParameters()
        if params is None:
            return False
        
        params.maxCurrent = value
        return self.setParameters(params)
    
    
    #----------------------------------------------------------------------------
    def getMaxPower(self):
        """
        Get the maximum power parameter
        
        Keyword arguments:
            None
        
        Return:
            Maximum watts (W) parameter , -1 if unable to read
        """
        
        params = self.getParameters()
        if params is None:
            return -1
        
        return params.maxPower
    
    
    #----------------------------------------------------------------------------
    def setMaxPower(self, value):
        """
        Set the maximum power parameter
        
        Keyword arguments:
            - value : Power (W)
        
        Return:
            True if successful, False otherwise
        """
        
        params = self.getParameters()
        if params is None:
            return False
        
        params.maxPower = value
        
        return self.setParameters(params)
    
    
    #----------------------------------------------------------------------------
    def isOutputEnabled(self):
        """
        Check if the PSU output is enabled
        
        Keyword arguments:
            None
        
        Return:
            True if enabled, False otherwise
        """
        
        params = self.getParameters()
        if params is None:
            return False
        
        return params.outputState
    
    
    #----------------------------------------------------------------------------
    def enableOutput(self):
        """
        Turn the output ON
        
        Keyword arguments:
            None        
        
        Return:
            True if successful, False otherwise
        """
        
        return self.setOutput(True)
    
    
    #----------------------------------------------------------------------------
    def disableOutput(self):
        """
        Turn the output OFF
        
        Keyword arguments:
            None        
        
        Return:
            True if successful, False otherwise
        """
        
        return self.setOutput(False)
    
    
    #----------------------------------------------------------------------------
    def setOutput(self, state):
        """
        Set the output ON or OFF
        
        Keyword arguments:
            - state : True=ON, False=OFF
        
        Return:
            True if successful, False otherwise
        """
        
        self.remote = True
        
        return self.send(self.COMMAND_CONTROLSTATE, [0x03 if state else 0x02]) is not None
    
    
    #----------------------------------------------------------------------------
    def enableRemoteControl(self):
        """
        Allows the PSU to be controlled remotely and disable the PSU local controls
        
        Keyword arguments:
            None
         
        Return: 
            True if successful, False otherwise
        """
        
        return self.setRemoteControl(True)
    
    
    #----------------------------------------------------------------------------
    def disableRemoteControl(self):
        """
        Enable the PSU local controls
        
        Keyword arguments:
            None
         
        Return: 
            True if successful, False otherwise
        """

        return self.setRemoteControl(False)
    
    
    #----------------------------------------------------------------------------
    def setRemoteControl(self, remote):
        """
        Sets wether or not the PSU can be controlled remotely
        
        Keyword arguments:
            remote : True: PC control (remote), False: Local control
        
        Return:
            True if successful, False otherwise
        """
        
        params = self.getParameters()
        if params is None:
            return False
        
        self.remote = remote
        
        state = 0x02 if remote else 0x00
        state = state | (0x01 if params.outputState else 0x00)
        
        return self.send(self.COMMAND_CONTROLSTATE, [state]) is not None
    
    
    #----------------------------------------------------------------------------
    def getInfo(self):
        """
        Returns the serial number, model number and firmware version of the psu364X
        
        Keyword arguments:
            None
            
        Return : psu364X.Info object containg the informations, None if unable to
                 read data.
        """
        
        data = self.send(self.COMMAND_READINFO)
        if data is None:
            return None
        
        info = Info()
        info.serial = data[3:9]
        info.model = data[9:14]
        info.version = float(struct.unpack_from('<H', data, 14)[0]) / 100
        
        return info



#=========================================================================================
#
# Info
#
#=========================================================================================
class Info:
    """
    Holds the informations received from the PSU with the command READINFO (0x8C)
    """
    
    serial = ""         # Serial number (6 bytes) #
    model = ""          # Model number (5 bytes) #
    version = 0.0       # Firmware version number #

    #----------------------------------------------------------------------------
    def __str__(self):
        """
        Returns the string representation of the this class
        
        Keyword arguments:
            None
        
        Return:
            String representation of the class
        """
        
        return "Model: {0}  S/N: {1}  FW Ver. {2}".format(
            self.model, self.serial, self.version)


    
#=========================================================================================
#
# Params
#
#=========================================================================================
class Params:
    """
    Holds the operating parameters received from the PSU using getParameters()
    
    Also used by setParameters(), but only voltageSet, maxVoltage, maxCurrent and maxPower
    are used
    """
    
    maxVoltage = 0.0            # Maximum allowable voltage #
    maxCurrent = 0.0            # Maximum allowable current #
    maxPower = 0.0              # Maximum allowable power #
    voltageSet = 0.0            # Current set voltage #
    measureVoltage = 0.0        # Actual voltage measurement (V) from the output #
    measureCurrent = 0.0        # Actual current measurement (A) from the output #
    measurePower = 0.0          # Actual power measurement (W) from the output #
        
    outputState = False         # Output active: True=ON, False=OFF
    excessiveCurrent = False    # Excessive current flag
    excessivePower = False      # Excessive power flag
    
    
    #----------------------------------------------------------------------------
    def __str__(self):
        """
        Returns the string representation of the this class
        
        Keyword arguments:
            None
            
        Return:
            String representation of the class
        """
        
        return "maxVoltage={0}V, maxCurrent={1}A, maxPower={2}W, voltageSet={3}V, measureVoltage={4}V, measureCurrent={5}A, measurePower={6}W, outputState={7}, excessiveCurrent={8}, excessivePower={9}".format(
            self.maxVoltage,
            self.maxCurrent,
            self.maxPower,
            self.voltageSet,
            self.measureVoltage,
            self.measureCurrent,
            self.measurePower,
            "ON" if self.outputState else "OFF",
            "True" if self.excessiveCurrent else "False",
            "True" if self.excessivePower else "False")



#=========================================================================================
#
# Exceptions
#
#=========================================================================================
class UnexpectedResponse(Exception): 
    """
    Raised if an invalid response frame is received from the PSU
    """

    pass