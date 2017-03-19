#!/usr/bin/env python
import os
import sys

D = os.path.dirname(os.path.realpath(__file__))
os.environ['MODULEPATH'] = os.path.join(D, 'modulefiles')
os.environ['LOADEDMODULES'] = ''
os.environ['_LMFILES_'] = ''
os.environ['PATH'] = '/usr/bin:/usr/sbin:/bin:/usr/local/bin:/opt/X11/bin'

sys.path.insert(0, os.path.join(D, '../lib'))
from shell import Shell
from module import Module
from module_loader import module_loader

def test_setenv():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    shell = Shell('bash')
    modulename = 'setenv'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables['SALAMI'] == '/opt/1'
    assert shell.variables['LOADEDMODULES'] == modulename
    assert shell.variables['_LMFILES_'] == filename

def test_unsetenv():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    os.environ['UNSETME'] = 'A VALUE'
    shell = Shell('bash')
    modulename = 'unsetenv'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables.get('UNSETME', None) is None
    os.environ['UNSETME'] = 'A VALUE'
    assert shell.variables['LOADEDMODULES'] == modulename
    assert shell.variables['_LMFILES_'] == filename

def test_path():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    shell = Shell('bash')
    modulename = 'path'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables['SALAMI'] == '/opt/0:/opt/1:/opt/2', 'E1.1'
    assert shell.variables['LOADEDMODULES'] == modulename, 'E1.2'
    assert shell.variables['_LMFILES_'] == filename, 'E1.3'
    module_loader('unload', modulename, shell)
    assert shell.variables['SALAMI'] is None, 'E2.1'
    assert shell.variables['LOADEDMODULES'] == '', 'E2.2'
    assert shell.variables['_LMFILES_'] == '', 'E2.3'

def test_alias():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    shell = Shell('bash')
    modulename = 'alias'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.aliases['FOO'] == 'this is a foo fun'
    assert shell.variables['LOADEDMODULES'] == modulename
    assert shell.variables['_LMFILES_'] == filename
    module_loader('unload', modulename, shell)
    assert shell.aliases['FOO'] is None
    assert shell.variables['LOADEDMODULES'] == ''
    assert shell.variables['_LMFILES_'] == ''

def test_function():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    shell = Shell('bash')
    modulename = 'function'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.functions['FOO'] == 'this is a foo fun $@', 'bad FOO set'
    assert shell.functions['FOO1'] == 'this is a foo fun $1', 'bad FOO1 set'
    assert shell.variables['LOADEDMODULES'] == modulename
    assert shell.variables['_LMFILES_'] == filename
    module_loader('unload', modulename, shell)
    assert shell.functions['FOO'] is None, 'FOO not unset'
    assert shell.functions['FOO1'] is None, 'FOO1 not unset'
    assert shell.variables['LOADEDMODULES'] == ''
    assert shell.variables['_LMFILES_'] == ''

def test_family():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    shell = Shell('bash')
    modulename = 'ucc/1.0'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables['MODULE_FAMILY_COMPILER'] == 'ucc', 'E1.1'
    assert shell.variables['MODULE_FAMILY_COMPILER_VERSION'] == '1.0', 'E1.2'
    assert shell.variables['MODULE_FAMILY_COMPILER_NAME'] == modulename, 'E1.3'
    assert shell.variables['LOADEDMODULES'] == modulename, 'E1.4'
    assert shell.variables['_LMFILES_'] == filename, 'E1.5'

    modulename = 'xcc/1.0'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables['MODULE_FAMILY_COMPILER'] == 'xcc', 'E2.1'
    assert shell.variables['MODULE_FAMILY_COMPILER_VERSION'] == '1.0', 'E2.2'
    assert shell.variables['MODULE_FAMILY_COMPILER_NAME'] == modulename, 'E2.3'
    assert shell.variables['LOADEDMODULES'] == modulename, 'E2.4'
    assert shell.variables['_LMFILES_'] == filename, 'E2.5'

def test_different_version():
    os.environ['LOADEDMODULES'] = ''
    os.environ['_LMFILES_'] = ''
    shell = Shell('bash')

    modulename = 'ucc/1.0'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables['MODULE_FAMILY_COMPILER'] == 'ucc', 'E1.1'
    assert shell.variables['MODULE_FAMILY_COMPILER_VERSION'] == '1.0', 'E1.2'
    assert shell.variables['MODULE_FAMILY_COMPILER_NAME'] == modulename, 'E1.3'
    assert shell.variables['LOADEDMODULES'] == modulename, 'E1.4'
    assert shell.variables['_LMFILES_'] == filename, 'E1.5'

    modulename = 'ucc/2.0'
    filename = os.path.join(D, 'modulefiles', modulename + '.py')
    module_loader('load', modulename, shell)
    assert shell.variables['MODULE_FAMILY_COMPILER'] == 'ucc', 'E2.1'
    assert shell.variables['MODULE_FAMILY_COMPILER_VERSION'] == '2.0', 'E2.2'
    assert shell.variables['MODULE_FAMILY_COMPILER_NAME'] == modulename, 'E2.3'
    assert shell.variables['LOADEDMODULES'] == modulename, 'E2.4'
    assert shell.variables['_LMFILES_'] == filename, 'E2.5'

def printc(message, end='\n'):
    sys.stdout.write(message + end)


if __name__ == '__main__':
    test_funs = [fun for (key, fun) in globals().items()
                 if key.startswith('test_')]
    for fun in test_funs:
        printc('{0:30s} '.format(fun.__name__+'...'), end='')
        try:
            fun()
            printc('pass')
        except AssertionError as e:
            print(e.args[0])
            printc('fail')
