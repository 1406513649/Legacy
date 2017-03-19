#!/usr/bin/env python
import os
import re
import sys
import os.path as op
from copy import deepcopy
from textwrap import wrap
from argparse import ArgumentParser, SUPPRESS, REMAINDER
from collections import OrderedDict
try:
    from itertools import izip_longest as zip_longest
except ImportError:
    from itertools import zip_longest

import shell as sh


PY_MODULE = 1
MODULEVERBOSITY = int(os.getenv('PY_MODULEVERBOSITY', 1))

TCL_MODULE = 2
TCL_MODULECMD = os.getenv('MODULECMD')

HOME = op.expanduser('~/')
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

LOADED   = '_loaded_'
UNLOADED = '_unloaded_'


def printc(*args):
    text = ' '.join(str(arg) for arg in args)
    sys.stderr.write(text + '\n')


class TCLModulesError(Exception): pass
class NotAModuleError(Exception): pass
class PrereqError(Exception): pass
class ConflictError(Exception): pass
class NoTCLModuleCommandError(Exception): pass


class Module(object):
    def __init__(self, modulename, filepath, loaded, 
                 on_load=None, on_unload=None):
        self.type = self.module_type(filepath)
        if self.type is None:
            raise NotAModuleError
        if self.type == TCL_MODULECMD:
            raise NoTCLModuleCommandError
        self.name = modulename
        self.path = filepath
        self.hidden = self.name.startswith('.')
        self._loaded = loaded
        x = op.split(self.name)
        if len(x) == 1:
            self.family = None
        else: 
            self.family = op.sep.join(x[:-1]).strip()
        self.on_load = on_load
        self.on_unload = on_unload

    def module_type(self, filepath):
        first_line = open(filepath).readline().rstrip()
        if first_line.startswith('#%Module'):
            return TCL_MODULE
        elif re.search(r'#!/.*\s+python', first_line):
            return PY_MODULE
        else:
            return None

    def set_status(self, status):
        if status == UNLOADED:
            self._loaded = False
        elif status == LOADED:
            self._loaded = True
        else:
            sh.raise_error('Unknown module status {0!r}'.format(status))
        if self._loaded and self.on_load:
            self.on_load(self)
        elif not self._loaded and self.on_unload:
            self.on_unload(self)

    @property
    def loaded(self):
        return self._loaded

    @loaded.setter
    def loaded(self, arg):
        self.set_status({True: LOADED, False: UNLOADED}[bool(arg)])

    def exec1(self, mode, namespace):
        output = {'_error': False}
        namespace['module_name'] = self.name
        namespace['module_path'] = self.path
        namespace['mode'] = mode 
        try:
            with open(self.path) as fh:
                exec(fh.read(), namespace, output)
        except SyntaxError as e:
            sh.raise_error('Failed to read module {0!r} with the following '
                           'error: {1}'.format(self.name, e.args[0]))
        except PrereqError as e:
            sh.raise_error('Prerequisite {0!r} missing for '
                           'module {1}'.format(e.args[0], self.name))
        except ConflictError as e:
            sh.raise_error('Module {0!r} conflicts with '
                           '{1!r}'.format(e.args[0], self.name))

        self.do_not_list = bool(output.get('do_not_list', 0))
        return
    

class SystemModules(object):
    def __init__(self):
        self.tcl_modulepath = sh.get_pathenv('MODULEPATH')
        self.py_modulepath = [p for p in sh.get_pathenv('PY_MODULEPATH')
                              if p not in self.tcl_modulepath]

        loaded_modules = sh.get_pathenv('PY_LOADEDMODULES')
        item = self.find_available(loaded_modules)
        self.avail, self._loaded, self.groups = item
        lmfiles = sh.get_pathenv('_PY_LMFILES_')

        if len(self._loaded) != len(lmfiles):
            sh.raise_error('Inconsistent LOADEDMODULES and LMFILES lengths')

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
                        module = Module(modulename, filepath, loaded,
                                        on_load=self.on_module_load,
                                        on_unload=self.on_module_unload)
                    except (NotAModuleError, NoTCLModuleCommandError):
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
            try:
                loaded = self.is_loaded(modulename)
                modulepath = op.realpath(modulename)
                module = Module(modulename, modulepath, loaded,
                                on_load=self.on_module_load,
                                on_unload=self.on_module_unload)
            except (NotAModuleError, NoTCLModuleCommandError):
                module = None
        elif op.isfile(op.join(os.getcwd(), modulename)):
            try:
                loaded = self.is_loaded(modulename)
                modulepath = op.join(os.getcwd(), modulename)
                module = Module(modulename, modulepath, loaded,
                                on_load=self.on_module_load,
                                on_unload=self.on_module_unload)
            except:
                module = None
        else:
            module = self.avail.get(modulename)
        return module

    def display_avail(self, terse=False):
        """Print available modules to the console"""
        height, width = sh.get_console_dims()
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
                sh.put_stderr(d1+':')
                sh.put_stderr('\n'.join(x.strip() for x in modules))
            else:
                sh.put_stderr('{0:-^{1}}'.format(d1, width))
                sh.put_stderr(format_text_to_cols(modules, width) + '\n')

    def display_loaded(self, terse=False):
        """Print loaded modules to the console"""
        height, width = sh.get_console_dims()
        if not self._loaded:
            sh.put_stderr('No modulefiles currently loaded.')
            return

        sh.put_stderr('Currently loaded modulefiles:')
        modules = ['{0})&{1}'.format(i+1, m.name) 
                   for (i, m) in enumerate(self._loaded)]
        if terse:
            sh.put_stderr('\n'.join(modules).replace('&', ' '))
        else:
            string = format_text_to_cols(modules, width)
            sh.put_stderr(string.replace('&', ' '))

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
        if TCL_MODULECMD:
            the_path.extend(self.tcl_modulepath)
        if join:
            return sh.path_join(the_path)
        return the_path
sys_modules = SystemModules()


class PyModuleCommand(object):
    def __init__(self, shell, v=MODULEVERBOSITY):
        self.shell = sh.get_shell(shell)
        self.verbosity = v

    def display_available_modules(self, terse=False):
        """Print available modules to the console"""
        sys_modules.display_avail(terse=terse)
        return 

    def list_loaded_modules(self, terse=False):
        """List all loaded modulues"""
        sys_modules.display_loaded(terse=terse)

    def getenv(self, name):
        return self.shell.getenv(name, os.environ.get(name))

    def unsetenv(self, name):
        self.shell.register_env(name, None, UNLOAD)

    def setenv(self, name, value):
        self.shell.register_env(name, value, LOAD)

    def get_path(self, pathname):
        # Check first if the path has already been modified and if not 
        # grab the value from the os environment
        if pathname in self.shell.environ:
            return sh.path_split(self.shell.getenv(pathname))
        return sh.path_split(os.environ.get(pathname))

    def modify_path(self, pathname, path, action):

        if 'darwin' in PLATFORM and pathname == 'LD_LIBRARY_PATH':
            # Modify path name for darwin 
            pathname = 'DYLD_LIBRARY_PATH'

        current_path = self.get_path(pathname)
        if not isinstance(path, (list, tuple)):
            path = path.split(os.pathsep)
        path = [sh.fixpath(x) for x in path]

        for p in path:
            if action == UNLOAD:
                if p in current_path:
                    current_path.remove(p)
                    if not current_path:
                        current_path = None

            elif action == 'remove':
                if p in current_path:
                    current_path.remove(p)

            elif action == 'prepend': 
                current_path.insert(0, p)

            else:
                current_path.append(p)

        the_path = sh.path_join(current_path)
        self.shell.register_env(pathname, the_path, LOAD)

    def remove_path(self, pathname, path):
        """Remove path from the pathname"""
        action = 'remove'
        self.modify_path(pathname, path, action)

    def prepend_path(self, pathname, path):
        """Prepend path to the pathname"""
        action = UNLOAD if self.mode == UNLOAD else 'prepend'
        self.modify_path(pathname, path, action)

    def append_path(self, pathname, path):
        """Prepend path to the pathname"""
        action = UNLOAD if self.mode == UNLOAD else 'append'
        self.modify_path(pathname, path, action)

    def set_alias(self, name, command):
        self.shell.register_alias(name, command, self.mode)

    def unset_alias(self, name):
        self.shell.register_alias(name, None, UNLOAD)

    @property
    def eval_dict(self):
        d = {'load_module': self.load_module,
             'unload_module': self.unload_module,
             'add_to_modulepath': self.add_to_modulepath,
             'swap_modules': self.swap_modules,
             #
             'prepend_path': self.prepend_path,
             'append_path': self.prepend_path,
             'remove_path': self.remove_path,
             #
             'set_alias': self.set_alias,
             'setenv': self.setenv,
             'unsetenv': self.unsetenv,
             'getenv': self.getenv,
             #
             'prereq': self.prereq,
             'conflict': self.conflict,
             #
             'shell_name': self.shell,
             'environ': dict(self.shell.environ),
             # os.path methods
             'isfile': op.isfile, 'isdir': op.isdir, 'exists': op.exists,
             'expanduser': op.expanduser,
             'join': op.join, 'os': os, 'sys': sys,
             'HOME': HOME, 'USER': USER, 'PLATFORM': PLATFORM,
             'HOSTNAME': HOSTNAME,
             #
             'get_output': sh.get_output,
             'put_stderr': sh.put_stderr,
             'raise_error': sh.raise_error,
             }
        return d

    def dump(self):

        the_path = sh.path_join([name for name in sys_modules.loaded(name=1)])
        self.shell.register_env('PY_LOADEDMODULES', the_path, LOAD)

        the_path = sh.path_join([path for path in sys_modules.loaded(path=1)])
        self.shell.register_env('_PY_LMFILES_', the_path, LOAD)

        s = self.shell.dump_environ()
        sh.put_stdout(s)

        if self.verbosity:
            loaded = ', '.join(sys_modules.loaded(name=1, this_session=1))
            unloaded = ', '.join(sys_modules.unloaded(name=1, this_session=1))
            msg = 'The following modules were {0}ed: {{0}}'.format(self.mode)
            if loaded:
                sh.put_stderr(msg.format(loaded))
            if unloaded:
                sh.put_stderr(msg.format(unloaded))

    def prereq(self, modulename, load_on_fail=None):
        if self.mode == UNLOAD:
            return
        for module in sys_modules:
            if not module.loaded:
                continue
            if modulename in (module.name, module.family):
                return
        if load_on_fail is not None:
            self.load_module(load_on_fail)
        elif sh.global_opts.force:
            self.load_module(modulename)
        else:
            raise PrereqError(modulename)

    def add_to_modulepath(self, dirpath):
        if not op.isdir(dirpath):
            sh.raise_error('{0!r} is not a directory'.format(dirpath))
        sys_modules.modify_modulepath(self.mode, dirpath)
        the_path = sys_modules.modulepath()
        self.shell.register_env('PY_MODULEPATH', the_path, LOAD)
        os.environ['PY_MODULEPATH'] = the_path

    def conflict(self, modulename):
        if self.mode == UNLOAD:
            return
        for module in sys_modules:
            if modulename in (module.name, module.family):
                if not module.loaded:
                    continue
                if sh.global_opts.force:
                    self.unload_module(modulename)
                else:
                    raise ConflictError(modulename)

    def find_module_file(self, modulename):
        return sys_modules.get_module(modulename)

    def call_tcl_modulecmd(self, subcmd, *args, **kwargs):
        raise_e = kwargs.get('raise_e', 0)
        try:
            return call_tcl_modulecmd(self.shell.name, subcmd, *args)
        except TCLModulesError as e:
            if raise_e:
                raise e
            return None

    def process_module(self, modulename, mode, raise_e=True):

        module = self.find_module_file(modulename)
        if module is None:
            if raise_e:
                sh.raise_error('Unable to locate a modulefile '
                               'for {0!r}'.format(modulename))
            return

        if mode == UNLOAD:
            if not module.loaded:
                return
            if module.type == TCL_MODULE:
                p = self.call_tcl_modulecmd(mode, module.name)
                sh.put_stdout(p['stdout'])
            else:
                # Execute the file
                self.exec_module(module)
            module.set_status(UNLOADED)
            return

        if sys_modules.is_loaded(module):
            if sh.global_opts.force:
                # Remove the module so it can be loaded
                self.unload_module(module.name)
            else:
                if self.verbosity:
                    sh.put_stderr('Module {0!r} is already '
                                  'loaded'.format(module.name))
                return

        # Execute the file
        if module.type == TCL_MODULE:
            p = self.call_tcl_modulecmd(mode, module.name)
            sh.put_stdout(p['stdout'])
        else:
            self.exec_module(module)
            if module.do_not_list:
                return
        module.set_status(LOADED)
        return

    def purge_from_cl(self):
        self.mode = UNLOAD
        for modulefile in [name for name in sys_modules.loaded(name=1)]:
            self.unload_module(modulefile)
        self.dump()

    def load_module(self, modulename):
        mode = UNLOAD if self.mode == UNLOAD else LOAD
        self.process_module(modulename, mode)

    def load_modules_from_cl(self, *modules):
        self.mode = LOAD
        for modulename in modules:
            self.process_module(modulename, LOAD)
        self.dump()

    def unload_module(self, modulename):
        self.process_module(modulename, UNLOAD)

    def unload_modules_from_cl(self, *modules):
        self.mode = UNLOAD
        for modulename in modules:
            self.process_module(modulename, UNLOAD)
        self.dump()

    def swap_modules_from_cl(self, module1, module2):
        self.mode = SWAP
        self.swap_modules(module1, module2)
        self.dump()

    def swap_modules(self, module1, module2):
        self.process_module(module1, UNLOAD, raise_e=True)
        self.process_module(module2, LOAD)

    def help1(self, *modules):
        self.mode = HELP
        for modulename in modules:
            module = self.find_module_file(modulename)
            if module.type == TCL_MODULE:
                try:
                    p = self.call_tcl_modulecmd('help', *modules)
                    sh.put_stderr(p['stderr'])
                    return
                except TCLModulesError:
                    sh.raise_error('Unable to locate a modulefile '
                                   'for {0!r}'.format(modulename))
            d = self.exec_module(module)
            try:
                string = d['help']().format(module_name=module.name, **d)
            except KeyError:
                string = '{0} - loads the {0} environment'.format(module.name)
            sh.put_stderr(string)

    def whatis1(self, *modules):
        self.mode = WHATIS
        for modulename in modules:
            module = self.find_module_file(modulename)
            if module.type == TCL_MODULE:
                try:
                    p = self.call_tcl_modulecmd('whatis', *modules)
                    sh.put_stderr(p['stderr'])
                    return
                except TCLModulesError:
                    sh.raise_error('Unable to locate a modulefile '
                                   'for {0!r}'.format(modulename))
            d = self.exec_module(module)
            try:
                string = d['whatis']().format(module_name=module.name, **d)
            except KeyError:
                string = 'loads the {0} environment'.format(module.name)
            sh.put_stderr(string)

    def exec_module(self, module):
        namespace = self.eval_dict
        module.exec1(self.mode, namespace)


def format_text_to_cols(array_of_str, width=None):

    if width is None:
        height, width = sh.get_console_dims()

    text = ' '.join(array_of_str)
    space = (width - len(''.join(array_of_str))) / len(array_of_str)
    if space >= 1:
        space = ' ' * int(space)
        return space.join(array_of_str)

    N, n = len(array_of_str), 2
    while True:
        # determine number of rows to print
        chnx = [array_of_str[i:i+n] for i in range(0, N, n)]
        cw = [max(len(x) for x in chnk) for chnk in chnx]
        rows = list(zip_longest(*chnx, fillvalue=''))
        lmax, text = -1, []
        for row in rows:
            a = ['{0:{1}s}'.format(row[i], w) for (i, w) in enumerate(cw)]
            text.append(' '.join(a))
            lmax = max(lmax, len(text[-1]))

        if lmax >= width:
            n += 1
            continue

        max_row_width = max(len(row) for row in text)
        num_col = len(cw)
        dif = width - max_row_width
        extra = int(dif / num_col)
        cw = [x+extra for x in cw]
        text2 = []
        for row in text:
            row = row.split() + ['']*(num_col-len(row.split()))
            a = ['{0:{1}s}'.format(row[i], w) for (i, w) in enumerate(cw)]
            text2.append(' '.join(a))
        return '\n'.join(text2)


def call_tcl_modulecmd(shell, subcmd, output_stream, *args, **kwargs):
    """Call the original [tcl] modulecmd"""
    if TCL_MODULECMD is None:
        raise TCLModulesError('MODULECMD envar not set')
    elif not op.isfile(TCL_MODULECMD):
        raise TCLModulesError('MODULECMD envar does not point to existing file')
    args = '' if not args else ' '.join(args)
    command = '{0} {1} {2} {3}'.format(TCL_MODULECMD, shell, subcmd, args)
    p = sh.get_output(command, full_output=1)
    if p['returncode'] != 0:
        raise TCLModulesError('call to modulecmd failed with the '
                              'following error: {1}'.format(subcmd, p['stderr']))
    return p



def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = ArgumentParser(prog='module')
    p.add_argument('shell', choices=('bash',))
    p.add_argument('--debug', action='store_true', default=False)
    p.add_argument('-v', default=MODULEVERBOSITY, type=int, 
            help='Level of verbosity [default: %(default)s]')
    p.add_argument('-c', action='store_true', default=False,
            help=('Call the c modulecmd (must define MODULECMD ' 
                  'environment variable)'))

    sub_p = p.add_subparsers(dest='subparser_name', 
                             title='subcommands',
                             description='valid subcommands',
                             help='sub-command help')

    p_avail = sub_p.add_parser('avail', help='Display available modules')
    p_avail.add_argument('-t', default=False, action='store_true', 
            help='Display available modules in terse format [default: False]')

    p_list = sub_p.add_parser('list', help='Display loaded modules')
    p_list.add_argument('-t', default=False, action='store_true', 
            help='Display available modules in terse format [default: False]')

    p_load = sub_p.add_parser('load', help='Load module[s]')
    p_load.add_argument('modulefile', nargs='+', help='Valid modulefile[s]')
    p_load.add_argument('-f', '--force', action='store_true', default=False,
            help='Force load missing prerequisites [default: False]')

    p_uload = sub_p.add_parser('unload', help='Unload module[s]')
    p_uload.add_argument('modulefile', nargs='+', help='Valid modulefile[s]')
    p_uload.add_argument('-f', '--force', action='store_true', default=False,
            help='Remove loaded prerequisites [default: False]')

    p_purge = sub_p.add_parser('purge', help='Unload all modules')

    p_swap = sub_p.add_parser('swap', help='Swap modules')
    p_swap.add_argument('modulefile', nargs=2, help='Valid modulefile')

    p_help = sub_p.add_parser('help', help='Display help for module[s]')
    p_help.add_argument('modulefile', nargs='+', help='Valid modulefile[s]')

    p_what = sub_p.add_parser('whatis', help='Display short help for module[s]')
    p_what.add_argument('modulefile', nargs='+', help='Valid modulefile[s]')

    args = p.parse_args(argv)

    if args.debug:
        sh.global_opts.debug = True

    try:
        sh.global_opts.force = args.force
    except AttributeError:
        pass

    p = PyModuleCommand(args.shell, v=args.v)

    if args.c:
        try:
            cargs = args.modulefile
        except AttributeError:
            cargs = []
        height, width = sh.get_console_dims()
        space = ' '*12
        text = wrap('***Warning: modules loaded/unloaded by calling TCL '
                    'modules cannot be tracked with this modules package '
                    'and is not recommended', width, subsequent_indent=space)
        sh.put_stderr('\n'.join(text))
        kwargs = {'sh_out': 1}
        p = call_tcl_modulecmd(args.shell, args.subparser_name, *cargs, **kwargs)
        if p['returncode'] != 0:
            sh.raise_error(p['stderr'])
        if subcmd in (AVAIL, LIST, HELP, WHATIS):
            sh.put_stderr(sh.to_string(p['stderr']))
        elif bool(p['stderr']):
            error(p['stderr'])
        else:
            sh.put_stderr(sh.to_string(p['stdout']))

    elif args.subparser_name == 'avail':
        p.display_available_modules(terse=args.t)

    elif args.subparser_name == 'list':
        p.list_loaded_modules(terse=args.t)

    elif args.subparser_name == 'load':
        p.load_modules_from_cl(*args.modulefile)

    elif args.subparser_name == 'unload':
        p.unload_modules_from_cl(*args.modulefile)

    elif args.subparser_name == 'swap':
        p.swap_modules_from_cl(*args.modulefile)

    elif args.subparser_name == 'help':
        p.help1(*args.modulefile)

    elif args.subparser_name == 'whatis':
        p.whatis1(*args.modulefile)

    elif args.subparser_name == 'purge':
        p.purge_from_cl()

    return 0


if __name__ == '__main__':
    main(sys.argv[1:])
