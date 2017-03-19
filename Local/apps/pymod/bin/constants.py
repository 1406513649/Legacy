import os
import sys

MODULEVERBOSITY = int(os.getenv('PY_MODULEVERBOSITY', 1))
TCL_MODULECMD = os.getenv('MODULECMD')

HOME = os.path.expanduser('~/')
USER = os.getenv('USER')
PLATFORM = sys.platform.lower()
HOSTNAME = os.getenv('HOSTNAME', '')

HELP   = 'help'
UNLOAD = 'unload'
LOAD   = 'load'
SWAP   = 'swap'
LIST   = 'list'
AVAIL  = 'avail'
WHATIS = 'whatis'

LOADED   = 'loaded'
UNLOADED = 'unloaded'

PY_MODULE = 'PYTHON'
TCL_MODULE = 'TCL'


