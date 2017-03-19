import os
import re

PY_MODULEFILE = 1
TCL_MODULEFILE = 2

class Module:
    def __init__(self, **dikt):
        self.name = dikt['name']
        self.fullname = dikt['fullname']
        self.path = dikt['path']
        self.realpath = dikt['realpath']
        self.type = dikt['type']
        self.version = dikt.get('version', None)
        self.loaded = dikt.get('loaded', False)
        self.default = False
        self.hidden = os.path.basename(self.realpath).startswith('.')

def is_module(filename):
    """Determine if the file is a module file or not"""
    if not os.path.exists(filename):
        return None

    if filename.endswith('.py'):
        # Assume the file is a module file
        return PY_MODULEFILE
    regex = re.compile(re.escape(r'#%Module'))
    if regex.search(open(filename).readline()):
        return TCL_MODULEFILE
    return None
