from __future__ import print_function

import os
import re
from collections import OrderedDict

import moduleio as io
from module import Module, is_module, PY_MODULEFILE, TCL_MODULEFILE
from utils import listdir


def find_modules(terse=False, tolerant=True):
    modulepath = os.getenv('MODULEPATH', '').split(os.pathsep)
    available_modules = _find_modules(modulepath, terse, tolerant)
    return available_modules

def _loaded_modules(disp=0, reverse=0):
    loaded = os.getenv('LOADEDMODULES', '').split(os.pathsep)
    lmfiles = os.getenv('_LMFILES_', '').split(os.pathsep)
    if len(loaded) != len(lmfiles):
        raise Exception('Inconsistent LOADEDMODULES and _LMFILES_ state')

    if not disp:
        if reverse:
            return reversed(loaded)
        return loaded
    if reverse:
        return list(zip(reversed(loaded), reversed(lmfiles)))
    return list(zip(loaded, lmfiles))

def _find_modules(modulepath, terse, tolerant):
    """Find all available modules on modulepath"""
    loaded_modules = _loaded_modules()

    splitext = os.path.splitext
    available_modules = OrderedDict()
    starting_dir = os.getcwd()

    for directory in modulepath:
        # Go through each module in the MODULEPATH and collect modules

        if not directory.split():
            # Skip empty entries
            continue

        if not os.path.isdir(directory):
            if tolerant:
                # Skip nonexistent directories
                continue
            raise Exception('Nonexistent directory in '
                            'MODULEPATH: {0!r}'.format(directory))

        # Collect modules in this directory
        this_dir_modules = []

        # change to directory and get modules
        # Files in the first level don't have name/version format, just name
        os.chdir(directory)
        files = listdir(directory, key=os.path.isfile)

        for filename in files:
            moduletype = is_module(filename)
            name = os.path.splitext(filename)[0]
            if moduletype is None:
                continue
            dikt = {'name': name,
                    'fullname': name,
                    'path': os.path.join(directory, filename),
                    'realpath': os.path.join(directory, filename),}

            if moduletype == TCL_MODULEFILE:
                # TCL module
                dikt['type'] = 'tcl'
            elif moduletype == PY_MODULEFILE:
                dikt['type'] = 'python'
            else:
                raise Exception('Unknown module type')
            dikt['loaded'] = dikt['fullname'] in loaded_modules
            this_dir_modules.append(Module(**dikt))

        # Look for modules 1 directory in
        # Modules 1 level in have name/version format
        dirs = listdir(directory, os.path.isdir)
        for dirname in dirs:
            default_module = None
            os.chdir(os.path.join(directory, dirname))
            for item in os.listdir('.'):
                if os.path.isdir(item):
                    io.log_warning('The following directory, nested more than 1 '
                                   'deep from a MODULEPATH directory, will not be '
                                   'searched: {0}'.format(item))
                    continue
                elif os.path.islink(item):
                    if item == 'default':
                        default_module = os.path.realpath(item)
                        if not os.path.isfile(default_module):
                            raise Exception('Default module symlink points to '
                                            'nonexistent file '
                                            '{0!r}'.format(default_module))
                        d = os.path.basename(os.path.dirname(default_module))
                        if d != dirname:
                            raise Exception('Default module symlink points to '
                                            'a file in a different directory')
                        continue
                    if not os.path.isfile(os.path.realpath(item)):
                        raise Exception('Symlink {0!r} points to '
                                        'nonexistent file'.format(item))

                moduletype = is_module(item)
                if moduletype is None:
                    continue

                name = dirname
                version = os.path.splitext(item)[0]
                fullname = os.path.join(name, version)
                path = os.path.join(directory, dirname, item)
                realpath = os.path.realpath(path)
                dikt = {'name': name,
                        'fullname': fullname,
                        'path': path,
                        'realpath': realpath,}

                if moduletype == TCL_MODULEFILE:
                    # TCL module
                    dikt['type'] = 'tcl'
                elif moduletype == PY_MODULEFILE:
                    dikt['type'] = 'python'
                    if re.search('^[0-9]', version):
                        # versioned
                        dikt['version'] = version
                else:
                    raise Exception('Unknown module type')
                dikt['loaded'] = dikt['fullname'] in loaded_modules
                this_dir_modules.append(Module(**dikt))

            # Set the default
            if default_module is not None:
                for module in this_dir_modules:
                    if module.realpath == default_module:
                        module.default = True
                        break
            else:
                # Determine if modules are versioned
                if any([module.version for module in this_dir_modules]):
                    this_dir_modules[-1].default = True

        fun = lambda x: x.fullname
        available_modules[directory] = sorted(this_dir_modules, key=fun)

    os.chdir(starting_dir)

    if terse:
        return [x.fullname for (k,v) in available_modules.items() for x in v]

    return available_modules


if __name__ == '__main__':
    print(find_modules())
    print(find_modules(terse=True))
