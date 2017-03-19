import os
import re
import sys
from copy import deepcopy
from available_modules import available_modules
from module_loader import module_loader

class _Shell(object):
    def __init__(self, environ=None):

        environ = environ or os.environ
        self._variables = dict([(k,v) for (k,v) in environ.items()])
        self._aliases = {}

        self.variables = dict([(k,v) for (k,v) in environ.items()])
        self.aliases = {}
        self.functions = {}

    def getenv(self, key, default=None):
        return self.variables.get(key, default)

    def setenv(self, key, val):
        self.variables[key] = val

    def unsetenv(self, key):
        self.variables[key] = None

    def set_alias(self, key, val):
        if re.search(r'\$[@1-9]', val):
            # shell function
            self.functions[key] = val
        else:
            self.aliases[key] = val

    def unset_alias(self, key):
        if key in self.functions:
            self.functions[key] = None
        elif key in self.aliases:
            self.aliases[key] = None

    def prepend_path(self, key, path):
        x = self.variables.get(key)
        if x is None:
            self.variables[key] = path
        else:
            self.variables[key] = path + os.pathsep + x

    def remove_path_first(self, key):
        x = self.variables.get(key)
        if x is not None:
            x = x.split(os.pathsep)[1:]
            if not x:
                self.variables[key] = None
            else:
                self.variables[key] = os.pathsep.join(x)

    def remove_path_last(self, key):
        x = self.variables.get(key)
        if x is not None:
            x = x.split(os.pathsep)[:-1]
            if not x:
                self.variables[key] = None
            else:
                self.variables[key] = os.pathsep.join(x)

    def append_path(self, key, path):
        x = self.variables.get(key)
        if x is None:
            self.variables[key] = path
        else:
            self.variables[key] = x + os.pathsep + path

    def remove_path(self, key, path):
        x = self.variables.get(key)
        if x is not None:
            x = x.split(os.pathsep)
            try:
                x.remove(path)
            except ValueError:
                pass
            if not x:
                self.variables[key] = None
            else:
                self.variables[key] = os.pathsep.join(x)

    def cleanup_path(self, key, must_exist=0):
        path = self.variables.get(key)
        if key is None:
            return
        path = path.split(os.pathsep)
        clean_path = []
        for p in path:
            if p in clean_path:
                continue
            if must_exist and not os.path.exists(p):
                continue
            clean_path.append(p)
        self.variables[key] = os.pathsep.join(clean_path)

    def dump(self):
        self.cleanup_path('PATH', must_exist=1)
        self.cleanup_path('MODULEPATH', must_exist=1)
        string = []
        for (key, val) in self.variables.items():
            if (key in self._variables and
                val == self._variables[key]):
                # Variable is unchanged
                continue
            string.append(self.expand_var(key, val=val))

        for (key, val) in self.functions.items():
            string.append(self.shell_function(key, val=val))

        for (key, val) in self.aliases.items():
            string.append(self.alias(key, val=val))

        return '\n'.join([x for x in string if x.split()])

    def register_module(self, mode, module):
        lm = self.variables.get('LOADEDMODULES', '').split(os.pathsep)
        _lm_ = self.variables.get('_LMFILES_', '').split(os.pathsep)
        if mode == 'load':
            lm.append(module.fullname)
            _lm_.append(module.realpath)
        elif mode == 'unload':
            if module.fullname in lm:
                lm.remove(module.fullname)
                _lm_.remove(module.realpath)
        lm = [x for x in lm if x.split()]
        _lm_ = [x for x in _lm_ if x.split()]
        self.variables['LOADEDMODULES'] = os.pathsep.join(lm)
        self.variables['_LMFILES_'] = os.pathsep.join(_lm_)

    def loaded_modules(self):
        return [m for m in available_modules if m.loaded]

    def load_module_by_name(self, mode, modulename):
        module_loader(mode, modulename, self)

    def display_modules(self, what, terse=False):
        available_modules.display(what, terse=terse)

    def get_module_by_name(self, modulename):
        return available_modules.get(modulename)

def Shell(shell, environ=None):
    if shell == 'bash':
        from bash import Bash
        return Bash(environ=environ)
