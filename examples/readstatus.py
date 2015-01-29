import os,sys
import colorama
import time

import psu364x


PORT = "/dev/ttyUSB0"
SPEED = 9600
ADDRESS = 0

try:
    
    print "Establishing communication with PSU..."
    psu = psu364x.Psu(PORT, ADDRESS, SPEED)
    
    print "\033[2J"
    
    while True:
        status = psu.getParameters()
        
        print """\033[0;0H
        Settings
        ========
         
        Set voltage     : {0:<6.2f}V  
        Maximum voltage : {4:<6.2f}V  
        Maximum current : {5:<6.2f}A  
        Maximum power   : {6:<6.12}W  

        
        Measurements
        ============
        Output state   : {7}
        Output mode    : {8}
        Output voltage : {1:<6.2f}V  
        Output current : {2:<6.2f}A  
        Output power   : {3:<6.2f}W  
        
        
        ******************************************
        
        Press CTRL-C to stop..
        """.format(
            status.voltageSet,
            status.measureVoltage,
            status.measureCurrent,
            status.measurePower,
            status.maxVoltage,
            status.maxCurrent,
            status.maxPower,
            "ON " if status.outputState else "OFF",
            "CC    " if status.excessiveCurrent else "Normal"
            )
        
        time.sleep(1)

except KeyboardInterrupt:
    
    print "\n\nClosing connection..."
    psu.close()

except psu364x.UnexpectedResponse as e:
    print "Unexpected response from PSU ({0})".format(str(e))
