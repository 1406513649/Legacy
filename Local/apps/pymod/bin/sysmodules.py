#!/usr/bin/env python
import os
import sys
import os.path as op
from collections import OrderedDict

import module as m2
import utilities as ut
from constants import *


class SystemModules(object):
    def __init__(self):
        self.tcl_modulepath = ut.get_pathenv('MODULEPATH')
        self.py_modulepath = [p for p in ut.get_pathenv('PY_MODULEPATH')
                              if p not in self.tcl_modulepath]

        loaded_modules = ut.get_pathenv('PY_LOADEDMODULES')
        item = self.find_available(loaded_modules)
        self.avail, self._loaded, self.groups = item
        lmfiles = ut.get_pathenv('_PY_LMFILES_')

        if len(self._loaded) != len(lmfiles):
            ut.raise_error('Inconsistent LOADEDMODULES and LMFILES lengths')

        self.loaded_this_session = []
        self.unloaded_this_session = []

    def __contains__(self, module):
        if module in self.avail.values():
            return True
        elif module in [m.name for m in self]:
            return True
        return False

    def __iter__(self):
        for item in self.avail.values():
            yield item

    def loaded(self, name=False, path=False, this_session=False):
        if this_session:
            loaded = self.loaded_this_session
        else:
            loaded = self._loaded
        if name:
            return [m.name for m in loaded]
        if path:
            return [m.path for m in loaded]
        return [m for m in loaded]

    def unloaded(self, name=False, path=False, this_session=False):
        if this_session:
            unloaded = self.unloaded_this_session
        else:
            unloaded = [m for m in self.avail if m not in self._loaded]
        if name:
            return [m.name for m in unloaded]
        if path:
            return [m.path for m in unloaded]
        return [m for m in unloaded]

    def modify_modulepath(self, mode, modulepath):
        if mode == UNLOAD:
            if modulepath in self.py_modulepath:
                self.py_modulepath.remove(modulepath)
        else:
            if modulepath not in self.py_modulepath:
                self.py_modulepath.append(modulepath)

        # Update available modules
        item = self.find_available(self.loaded(name=1), remove=mode==UNLOAD)
        self.avail, self._loaded, self.groups = item

    def find_available(self, loaded_modules, remove=False):
        avail, groups = OrderedDict(), []
        for directory in self.modulepath(join=0):
            for (dirname, dirs, files) in os.walk(directory):
                this_group = []
                d = dirname.replace(directory, '')
                for filename in files:
                    filepath = op.join(dirname, filename)
                    modulename = op.join(d, filename).lstrip(op.sep)
                    loaded = modulename in loaded_modules
                    try:
                        module = m2.Module(filepath, name=modulename,
                                           loaded=loaded,
                                           on_load=self.on_module_load,
                                           on_unload=self.on_module_unload)
                    except (m2.NotAModuleError, m2.NoTCLModuleCommandError):
                        continue
                    if module.name not in avail:
                        # Precedence to modules earlier in path
                        avail[module.name] = module
                    this_group.append(module.name)
                groups.append((dirname, this_group))
        loaded = [avail[m] for m in loaded_modules]

        if remove:
            # tjfulle: should be logic for unloading modules that are 
            # already loaded but no longer on the path
            pass

        return avail, loaded, groups

    def get_module(self, modulename):
        if op.isfile(op.realpath(modulename)):
            # Precedent to actual files
            try:
                loaded = self.is_loaded(modulename)
                modulepath = op.realpath(modulename)
                module = m2.Module(modulepath, name=modulename, loaded=loaded,
                                   on_load=self.on_module_load,
                                   on_unload=self.on_module_unload)
            except (m2.NotAModuleError, m2.NoTCLModuleCommandError):
                module = None
        elif op.isfile(op.join(os.getcwd(), modulename)):
            try:
                loaded = self.is_loaded(modulename)
                modulepath = op.join(os.getcwd(), modulename)
                module = m2.Module(modulepath, name=modulename, loaded=loaded,
                                   on_load=self.on_module_load,
                                   on_unload=self.on_module_unload)
            except:
                module = None
        else:
            module = self.avail.get(modulename)
        return module

    def display_avail(self, terse=False):
        """Print available modules to the console"""
        height, width = ut.get_console_dims()
        for (d1, group) in self.groups:
            modules = []
            for name in group:
                m = self.avail[name]
                if m.hidden:
                    continue
                modules.append(m.name)
                if m.loaded:
                    modules[-1] += '*'
            if terse:
                ut.put_stderr(d1+':')
                ut.put_stderr('\n'.join(x.strip() for x in modules))
            else:
                ut.put_stderr('{0:-^{1}}'.format(d1, width))
                ut.put_stderr(ut.format_text_to_cols(modules, width) + '\n')

    def display_loaded(self, terse=False):
        """Print loaded modules to the console"""
        height, width = ut.get_console_dims()
        if not self._loaded:
            ut.put_stderr('No modulefiles currently loaded.')
            return

        ut.put_stderr('Currently loaded modulefiles:')
        modules = ['{0})&{1}'.format(i+1, m.name) 
                   for (i, m) in enumerate(self._loaded)]
        if terse:
            ut.put_stderr('\n'.join(modules).replace('&', ' '))
        else:
            string = ut.format_text_to_cols(modules, width)
            ut.put_stderr(string.replace('&', ' '))

    def on_module_unload(self, module):
        if self.is_loaded(module):
            self._loaded.remove(module)
            self.unloaded_this_session.append(module)

    def on_module_load(self, module):
        if not self.is_loaded(module):
            self._loaded.append(module)
            self.loaded_this_session.append(module)

    def is_loaded(self, module):
        if module in self._loaded:
            return True
        if module in [m.name for m in self._loaded]:
            return True
        return False

    def modulepath(self, join=1):
        the_path = self.py_modulepath
        if ut.tcl_module_command():
            the_path.extend(self.tcl_modulepath)
        if join:
            return ut.path_join(the_path)
        return the_path
sys_modules = SystemModules()


if __name__ == '__main__':
    sys_modules.display_avail()
    sys_modules.display_loaded()
