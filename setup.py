try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'description': 'Module for controlling Array 364X power supplies',
    'author': 'Benoit Frigon',
    'license': 'GPL',
    'url': 'http://www.bfrigon.com/python-psu364x',
    'author_email': 'benoit@frigon.info',
    'version': '0.1',
    'install_requires': ['pyserial'],
    'packages': ['psu364x'],
    'name': 'psu364x'
}

setup(**config) 
