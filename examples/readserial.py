import os,sys
import psu364x

PORT = "/dev/ttyUSB0"
SPEED = 9600
ADDRESS = 0

try:
    
    print "Establishing communication with PSU...\n\n"
    psu = psu364x.Psu(PORT, ADDRESS, SPEED)

    info = psu.getInfo()
    
    print "Power supply {0}, serial number {1}".format(info.model, info.serial)
    
    
    print "\n\nClosing connection..."
    psu.close()

except psu364x.UnexpectedResponse as e:
    print "Unexpected response from PSU ({0})".format(str(e))
