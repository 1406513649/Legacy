#!/usr/bin/env python
import os
import re
import sys
import os.path as op
from copy import deepcopy
from textwrap import wrap
from argparse import ArgumentParser, SUPPRESS, REMAINDER

from constants import *
import utilities as ut
from shell import shell
from sysmodules import sys_modules


class PrereqError(Exception): pass
class ConflictError(Exception): pass


def printc(*args):
    text = ' '.join(str(arg) for arg in args)
    sys.stderr.write(text + '\n')


class PyModuleCommand(object):
    def __init__(self, v=MODULEVERBOSITY):
        self.verbosity = v

    def display_available_modules(self, terse=False):
        """Print available modules to the console"""
        sys_modules.display_avail(terse=terse)
        return 

    def list_loaded_modules(self, terse=False):
        """List all loaded modulues"""
        sys_modules.display_loaded(terse=terse)

    def getenv(self, name):
        return shell.getenv(name, os.environ.get(name))

    def unsetenv(self, name):
        if self.mode == UNLOAD:
            return
        shell.register_env(name, None, 'unset')

    def setenv(self, name, value):
        action = 'unset' if self.mode == UNLOAD else 'set'
        shell.register_env(name, value, action)

    def get_path(self, pathname):
        # Check first if the path has already been modified and if not 
        # grab the value from the os environment
        if pathname in shell.environ:
            return ut.path_split(shell.getenv(pathname))
        return ut.path_split(os.environ.get(pathname))

    def modify_path(self, pathname, path, action):

        if 'darwin' in PLATFORM and pathname == 'LD_LIBRARY_PATH':
            # Modify path name for darwin 
            pathname = 'DYLD_LIBRARY_PATH'

        current_path = self.get_path(pathname)
        if not isinstance(path, (list, tuple)):
            path = path.split(os.pathsep)
        path = [ut.fixpath(x) for x in path]

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

        the_path = ut.path_join(current_path)
        shell.register_env(pathname, the_path, LOAD)

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
        shell.register_alias(name, command, self.mode)

    def unset_alias(self, name):
        shell.register_alias(name, None, UNLOAD)

    def dump(self):

        the_path = ut.path_join([name for name in sys_modules.loaded(name=1)])
        shell.register_env('PY_LOADEDMODULES', the_path, LOAD)

        the_path = ut.path_join([path for path in sys_modules.loaded(path=1)])
        shell.register_env('_PY_LMFILES_', the_path, LOAD)

        s = shell.dump_environ()
        ut.put_stdout(s)

        if self.verbosity:
            loaded = ', '.join(sys_modules.loaded(name=1, this_session=1))
            unloaded = ', '.join(sys_modules.unloaded(name=1, this_session=1))
            if loaded:
                msg = 'The following modules were loaded: {0}'
                ut.put_stderr(msg.format(loaded))
            if unloaded:
                msg = 'The following modules were unloaded: {0}'
                ut.put_stderr(msg.format(unloaded))

    def prereq(self, prereq_module, load_on_fail=None):
        if self.mode == UNLOAD:
            return
        for module in sys_modules.loaded():
            if prereq_module in (module.name, module.family):
                return
        if ut.global_opts.force:
            self.load_module(prereq_module)
        elif load_on_fail:
            self.load_module(load_on_fail)
        else:
            raise PrereqError(prereq_module)

    def add_to_modulepath(self, dirpath):
        if not op.isdir(dirpath):
            ut.raise_error('{0!r} is not a directory'.format(dirpath))
        sys_modules.modify_modulepath(self.mode, dirpath)
        the_path = sys_modules.modulepath()
        shell.register_env('PY_MODULEPATH', the_path, LOAD)
        os.environ['PY_MODULEPATH'] = the_path

    def conflict(self, modulename):
        if self.mode == UNLOAD:
            return
        for module in sys_modules.loaded():
            if modulename in (module.name, module.family):
                if ut.global_opts.force:
                    self.unload_module(modulename)
                else:
                    raise ConflictError(modulename)

    def get_module(self, modulename):
        return sys_modules.get_module(modulename)

    def process_module(self, modulename, mode, raise_e=True):

        module = self.get_module(modulename)
        if module is None:
            if raise_e:
                ut.raise_error('Unable to locate a modulefile '
                               'for {0!r}'.format(modulename))
            return

        if mode == UNLOAD and not module.loaded:
            return

        elif mode == LOAD and module.loaded:
            if ut.global_opts.force:
                # Remove the module so it can be loaded
                self.unload_module(module.name)
            else:
                if self.verbosity:
                    ut.put_stderr('Module {0!r} is already '
                                  'loaded'.format(module.name))
                return

        p = module.load(mode=mode)

        if module.type == TCL_MODULE:
            if p['stderr'] and mode not in (WHATIS, HELP):
                ut.raise_error('TCL Module failed to {0} with the '
                               'following error: {1}'.format(mode, p['stderr']))
            ut.put_stdout(p['stdout'])

        else:
            errors = module.load_errors()
            if errors:
                ut.raise_error('{0!r} failed to load with the following errors:'
                           '\n\t{1}'.format(module.name, '\n\t'.join(errors)))

            for (command, args) in module.cc:
                try:
                    getattr(self, command)(*args)
                except PrereqError as e:
                    ut.raise_error('Prerequisite {0!r} missing for '
                                   'module {1}'.format(e.args[0], module.name))
                except ConflictError as e:
                    ut.raise_error('Module {0} conflicts with loaded '
                                   'module {1}'.format(module.name, e.args[0]))

        status = {LOAD: LOADED, UNLOAD: UNLOADED}.get(mode)
        if status is not None and not module.hidden:
            module.set_status(status)

        return

    def purge_from_cl(self):
        self.mode = UNLOAD
        for modulefile in [name for name in sys_modules.loaded(name=1)]:
            self.unload_module(modulefile)
        self.dump()

    def load_module(self, modulename):
        """Load the module"""
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
        for modulename in modules:
            module = self.get_module(modulename)
            if module is None:
                ut.raise_error('Module not found: {0!r}'.format(modulename))
            s = module.help1()
            ut.put_stderr(s)

    def whatis1(self, *modules):
        self.mode = WHATIS
        if not modules:
            modules = sys_modules.avail.values()
        else:
            modules = [self.get_module(m) for m in modules]
        xm = max([len(m.name) for m in modules]) + 1
        text = []
        for m in modules:
            if m is None:
                s = '***WARNING: Module {0!r} not found'.format(m.name)
                ut.put_stderr(s)
            elif m.hidden:
                continue
            else:
                s = m.whatis()
                if m.type == TCL_MODULE:
                    s = s.split(':', 1)[1].strip()
                text.append('{0:{1}s}: {2}'.format(m.name, xm, s.strip()))
        ut.put_stderr('\n'.join(text))


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    p = ArgumentParser(prog='module')
    #p.add_argument('shell', choices=('bash',))
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
    p_what.add_argument('modulefile', nargs='*', help='Valid modulefile[s]')

    args = p.parse_args(argv)

    if args.debug:
        ut.global_opts.debug = True

    try:
        ut.global_opts.force = args.force
    except AttributeError:
        pass

    #p = PyModuleCommand(args.shell, v=args.v)
    p = PyModuleCommand(v=args.v)

    if args.c:
        try:
            cargs = args.modulefile
        except AttributeError:
            cargs = []
        height, width = ut.get_console_dims()
        space = ' '*12
        text = wrap('***Warning: modules loaded/unloaded by calling TCL '
                    'modules cannot be tracked with this modules package '
                    'and is not recommended', width, subsequent_indent=space)
        ut.put_stderr('\n'.join(text))
        kwargs = {'sh_out': 1}
        p = ut.call_tcl_modulecmd(shell.name, args.subparser_name, 
                                  *cargs, **kwargs)
        if p['returncode'] != 0:
            ut.raise_error(p['stderr'])
        if args.subparser_name in (AVAIL, LIST, HELP, WHATIS):
            ut.put_stderr(ut.to_string(p['stderr']))
        elif bool(p['stderr']):
            error(p['stderr'])
        else:
            ut.put_stderr(ut.to_string(p['stdout']))

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
