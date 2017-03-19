import re
import os
import sys
import os.path as op
from collections import OrderedDict
from textwrap import wrap

import shell as sh
import utilities as ut
from constants import *


class NotAModuleError(Exception): pass
class NoTCLModuleCommandError(Exception): pass


class CommandCollector(object):
    def __init__(self):
        self.data = []
    def put(self, item):
        assert len(item) == 2
        if not isinstance(item[1], (list, tuple)):
            item = (item[0], (item[1],))
        self.data.append(item)
    def getall(self, command):
        xc = []
        for (x, args) in self.data:
            if x == command:
                xc.append(args)
        return xc

    def __iter__(self):
        for (command, args) in self.data:
            yield command, args

class Module(object):
    def __init__(self, filename, name=None, loaded=False,
                 on_load=None, on_unload=None):

        if not op.isfile(filename):
            raise ut.FileNotFoundError(filename)

        first_line = open(filename).readline().rstrip()
        if first_line.startswith('#%Module'):
            self.type = TCL_MODULE
        elif re.search(r'#!/.*\s+python', first_line):
            self.type = PY_MODULE
        else:
            raise NotAModuleError
        if self.type == TCL_MODULE and not ut.tcl_module_command():
            raise NoTCLModuleCommandError

        self.exec_order = []
        self.filename = filename
        self.path = op.realpath(filename)
        if name is None:
            name = op.basename(self.filename)
        self.name = name

        self.on_load = on_load
        self.on_unload = on_unload
        self._loaded = loaded
        self._path_modified = False
        self.assert_true = []
        self.family = self.determine_family()
        self.hidden = self.name.startswith('.')

    def set_status(self, status):
        if status == 'unloaded':
            self._loaded = False
        elif status == 'loaded':
            self._loaded = True
        else:
            ut.raise_error('Unknown module status {0!r}'.format(status))
        if self._loaded and self.on_load:
            self.on_load(self)
        elif not self._loaded and self.on_unload:
            self.on_unload(self)

    @property
    def loaded(self):
        return self._loaded

    def p_add_to_modulepath(self, path):
        """Adds path to the module search path"""
        if not isinstance(path, (list, tuple)):
            path = path.split(os.pathsep)
        self.cc.put(('add_to_modulepath', path))

    @property
    def p_module_name(self):
        return self.name

    @property
    def p_module_path(self):
        return self.path

    def p_prereq(self, modulename, load_on_fail=None):
        """Module prerequisites"""
        self.cc.put(('prereq', (modulename, load_on_fail)))

    def p_conflict(self, modulename):
        """Module conflicts"""
        self.cc.put(('conflict', modulename))

    def p_prepend_path(self, pathname, path):
        """Prepend the path to the pathname environment variable"""
        if not isinstance(path, (list, tuple)):
            path = path.split(os.pathsep)
        self.cc.put(('prepend_path', (pathname, path)))
        self._path_modified = True

    def p_append_path(self, pathname, path):
        """Append the path to the pathname environment variable"""
        if not isinstance(path, (list, tuple)):
            path = path.split(os.pathsep)
        self.cc.put(('append_path', (pathname, path)))
        self._path_modified = True

    def p_remove_path(self, pathname, path):
        """Remove the path to the pathname environment variable"""
        if not isinstance(path, (list, tuple)):
            path = path.split(os.pathsep)
        self.cc.put(('remove_path', (pathname, path)))
        self._path_modified = True

    def p_load_module(self, modulename):
        """Load the module modulename"""
        self.cc.put(('load_module', modulename))

    def p_unload_module(self, modulename):
        """Unload the module modulename"""
        self.cc.put(('unload_module', modulename))

    def p_swap_modules(self, module1, module2):
        """Load the module modulename"""
        self.cc.put(('swap_modules', (module1, module2)))

    def p_set_alias(self, name, command):
        self.cc.put(('set_alias', (name, command)))

    def p_unset_alias(self, name, command):
        self.cc.put(('unset_alias', (name, command)))

    def p_setenv(self, name, command):
        self.cc.put(('setenv', (name, command)))

    def p_unsetenv(self, name):
        self.cc.put(('unsetenv', name))

    def p_assert_true(self, condition, on_fail):
        self.assert_true.append((condition, on_fail))

    @property
    def assertion_errors(self):
        return [x[1] for x in self.assert_true if not x[0]]

    def namespace(self):
        ns = dict([(k[2:], getattr(self, k)) 
                   for k in dir(self) if k.startswith('p_')])
        ns.update({
            # os.path methods
            'isfile': op.isfile, 'isdir': op.isdir, 'exists': op.exists,
            'expanduser': op.expanduser, 'join': op.join, 
            #
            'os': os, 'sys': sys,
            #
            'HOME': HOME, 'USER': USER, 
            'PLATFORM': PLATFORM, 'HOSTNAME': HOSTNAME,
             #
             'get_output': ut.get_output,
             'put_stderr': ut.put_stderr,
             'raise_error': ut.raise_error,
             #
             'shell_name': sh.shell.name,
             'environ': dict(sh.shell.environ),
             'getenv': self.getenv,
             })
        return ns

    def getenv(self, name):
        return sh.shell.getenv(name, os.environ.get(name))

    def load(self, mode=None):
        self.cc = CommandCollector()
        p = self._load(mode)
        return p

    def _load(self, mode):
        """Load the module"""

        if self.type == TCL_MODULE:
            p = self.call_tcl_modulecmd(mode, self.name)
            return p

        ns_o = {}
        ns = self.namespace()
        ns['mode'] = mode
        try:
            with open(self.path) as fh:
                exec(fh.read(), ns, ns_o)

        except SyntaxError as e:
            ut.raise_error('The module file {0!r} contains python '
                            'syntax errors'.format(self.path))

        self.description = ns_o.get('description')
        self._whatis = ns_o.get('whatis')

        return

    def call_tcl_modulecmd(self, subcmd, *args, **kwargs):
        raise_e = kwargs.get('raise_e', 0)
        try:
            return ut.call_tcl_modulecmd(sh.shell.name, subcmd, *args)
        except ut.TCLModulesError as e:
            if raise_e:
                raise e
            p = {'returncode': 2, 'stderr': e.args[0]}
            return p

    def determine_family(self):
        x = op.split(self.name)
        if len(x) == 1:
            return None
        return op.sep.join(x[:-1]).strip()

    def load_errors(self):
        e1 = self.assertion_errors
        return e1

    def whatis(self):

        p = self.load('whatis')
        if self.type == TCL_MODULE:
            return p['stderr']

        if self._whatis:
            s = self._whatis
        elif self.description:
            s = self.description
        else:
            s = 'Loads the {0!r} environment'.format(self.name)
        return s

    def help1(self):

        height, width = ut.get_console_dims()

        p = self.load('help')
        if self.type == TCL_MODULE:
            return p['stderr']

        s = 'Loads the {0!r} environment'.format(self.name)

        if self.description is not None:
            s += '\n\nDescription:\n\t'
            desc = wrap(self.description, width-8, subsequent_indent='\t')
            s += '\n'.join(desc)

        prereqs = [x[0] for x in self.cc.getall('prereq')]
        if prereqs:
            s += '\n\nModule prerequisites:'
            s += '\n\t{0}'.format(', '.join(prereqs))

        conflicts = [x[0] for x in self.cc.getall('conflict')]
        if conflicts:
            s += '\n\nModule conflicts with the following modules:'
            s += '\n\t{0}'.format(', '.join(conflicts))

        envs_to_set = self.cc.getall('setenv')
        if envs_to_set:
            s += '\n\nThe following environment variables are set:'
            for (name, value) in envs_to_set:
                s += '\n\t{0}: {1}'.format(name, value)

        if self._path_modified:
            s += '\n\nThe following paths are modified:'
            for (key, path) in self.cc.getall('prepend_path'):
                p = os.pathsep.join(path)
                s += '\n\t{0} (prepended with: {1})'.format(key, p)
            for (key, path) in self.cc.getall('append_path'):
                p = os.pathsep.join(path)
                s += '\n\t{0} (appended with: {1})'.format(key, p)
            for (key, path) in self.cc.getall('remove_path'):
                p = os.pathsep.join(path)
                s += '\n\t{0} (removed from: {1})'.format(key, p)

        p = [x[0] for x in self.cc.getall('add_to_modulepath')]
        if p:
            s += '\n\nThe following are added to the module search path:'
            s += '\n\t{0}'.format(', '.join(p))

        p = [x[0] for x in self.cc.getall('load_module')]
        if p:
            s += '\n\nThe following modules are loaded:'
            s += '\n\t{0}'.format(', '.join(p))

        p = [x[0] for x in self.cc.getall('unload_module')]
        if p:
            s += '\n\nThe following modules are unloaded:'
            s += '\n\t{0}'.format(', '.join(p))

        p = self.cc.getall('swap_modules')
        if p:
            s += '\n\nThe following modules are swapped:\n\t'
            for (m1, m2) in p:
                s += '{0} <-> {1}, '.format(m1, m2)
            s = s.rstrip(', ')

        p = [x[0] for x in self.cc.getall('set_alias')]
        if p:
            a = ', '.join(p)
            s += '\n\nThe following aliases are set:\n\t{0}'.format(a)

        return s


def test():
    import shell as sh
    mod = Module('foo')
    mod.load()
    print(mod.help1())
    print(mod.family)
    print(mod.hidden)
    print(mod.whatis())
    print(mod.load_errors())


if __name__ == '__main__':
    test()
