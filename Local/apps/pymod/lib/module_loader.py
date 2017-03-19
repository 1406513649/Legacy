import os
import sys

import moduleio as io
from available_modules import available_modules

from modify_path import append_path, prepend_path, remove_path
from sys_platform import platform, ModuleSkipPlatform
from prereq import prereq
from set_alias import set_alias, unset_alias
from setenv import setenv, unsetenv
from utils import getuser, hostname, system, uname
from module_family import family
from module_versions import version_control

def module_loader(mode, modulename, shell):
    """Wrapper to sandbox_run. if modulename is available, the module is
       instantiated and passed on

    """
    module = available_modules.get(modulename)
    if module is None:
        message = 'The following module(s) are unknown: {0!r}'.format(modulename)
        io.log_error_and_exit('module_loader.py', message)
    return sandbox_run(mode, module, shell)

def sandbox_run(mode, module, shell):
    """Load the module"""

    if mode == 'load' and module.loaded:
        io.log_message('Module {0!r} is already loaded'.format(module.fullname))
        return

    # Check if a module of different version already loaded, and unload it if so
    version_control(mode, module, shell)
    exec_space = {'mode': lambda: mode,
                  'module_name': lambda: module.name,
                  'module_path': lambda: module.realpath,
                  'module_version': lambda: module.version,
                  'module_fullname': lambda: module.fullname,
                  'setenv': lambda k, v: setenv(mode, k, v, shell),
                  'unsetenv': lambda k: unsetenv(mode, k, shell),
                  'set_alias': lambda k, v: set_alias(mode, k, v, shell),
                  'unset_alias': lambda k: unset_alias(mode, k, shell),
                  'append_path': lambda k, v: append_path(mode, k, v, shell),
                  'remove_path': lambda k, v: remove_path(mode, k, v, shell),
                  'prepend_path': lambda k, v: prepend_path(mode, k, v, shell),
                  'log_error': lambda x: io.raise_error(x),
                  'log_warning': lambda x: io.log_warning(module.realpath, x),
                  'log_message': lambda x: io.log_message(x, 2),
                  'platform': platform,
                  'prereq': lambda x: prereq(module.fullname, x),
                  'family': lambda x: family(mode, x, module, shell),
                  'getuser': getuser, 'hostname': hostname, 'uname': uname,
                  'HOME': os.path.expanduser('~/'),
                  'system': system,
                  'os': os, 'sys': sys,
                  'load': lambda x: module_loader('load', x, shell),
                  'unload': lambda x: module_loader('unload', x, shell),
    }

    ns = {}
    try:
        with open(module.realpath) as fh:
            code = compile(fh.read(), module.fullname, 'exec')
            exec(code, exec_space, ns)
    except io.ModuleError as e:
        io.log_error_and_exit(module.realpath, e.args[0])
    except ModuleSkipPlatform as e:
        # Skip this module on this platform
        return None
    except NameError as e:
        message = 'Failed to load {0} with the following '\
                  'error: {1}'.format(module.fullname, e.args[0])
        io.log_error_and_exit(module.realpath, message)

    module.namespace = ns
    shell.register_module(mode, module)


if __name__ == '__main__':
    from shell import Shell
    from module import Module
    d = os.path.dirname(os.path.realpath(__file__))
    filename = sys.argv[1]
    shell = Shell('bash')
    dikt = {'name': os.path.basename(filename),
            'version': None,
            'type': 'python' if filename.endswith('.py') else 'tcl',
            'fullname': os.path.basename(filename),
            'path': filename,
            'realpath': os.path.realpath(filename),
            'loaded': False,
            'default': False,}
    module = Module(**dikt)
    sandbox_run('load', module, shell)
    string = shell.dump()
    print(string)
