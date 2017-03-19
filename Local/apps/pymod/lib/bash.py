import os
import re
from copy import deepcopy
from shell import _Shell

class Bash(_Shell):
    name = 'bash'
    def expand_var(self, key, val=None):
        """Define variable in bash syntax"""
        if val is None:
            return 'unset {0};'.format(key)
        else:
            return '{0}="{1}";export {0};'.format(key, val)

    def shell_function(self, key, val=None):
        # Define or undefine a bash shell function.
        # Modify module definition of function so that there is
        # one and only one semicolon at the end.
        if val is None:
            return 'unset -f {0} 2> /dev/null || true;'.format(key)
        else:
            val = val.rstrip(';')
            return 'function {0} {{ {1}; }};'.format(key, val)

    def alias(self, key, val=None):
        # Define or undefine a bash shell alias.
        # Modify module definition of function so that there is
        # one and only one semicolon at the end.
        if val is None:
            return 'unalias {0} 2> /dev/null || true;'.format(key)
        else:
            val = val.rstrip(';')
            return 'alias {0}={1!r};'.format(key, val)
