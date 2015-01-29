
Python psu364x
==============

This python library provides basic functions for controlling Array 3600 series bench power supplies (3644,3645,3646)

These power supplies are rebadged under many names, so it should also work with :
* Array 3644A, 3645A and 3646A
* Circuit Specialist 3644A, 3645A and 3646A
* 3com 364x

What it does
------------

* Read/Set operating parameters (max. current, max. power, max. voltage, voltage set)
* Measure output parameters (output state, output voltage, output current, output power)
* Set output ON-OFF
* Read serial number, model number and firmware version

What it does not do
-------------------

* Calibration. The commands needed for calibration are not implemented yet.

--------------------------------------------------

Dependencies
------------

* pyserial


Installation
------------

If you already have Python and pip on your system you can install the library simply by running:

```shell
pip install psu364x
```

**-OR-**

```
git clone https://github.com/bfrigon/python-psu364x.git

cd python-psu364x

python setup.py install

```


--------------------------------------------------


Usage
------------

```python
import psu364x

psu = psu364x.Psu("/dev/ttyUSB0", 0, 9600)  # Device, PSU address, speed

status = psu.getParameters()
print status

psu.close()
```
