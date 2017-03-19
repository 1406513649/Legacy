import os
from collections import OrderedDict

from find_modules import find_modules
from moduleio import log_message, colors, format_text_to_cols
from utils import get_console_dims

class AvailableModules:
    def __init__(self):
        self._available_modules = find_modules()

    def get(self, name, byname=0):
        is_filepath = os.path.isfile(name)
        for (directory, modules) in self._available_modules.items():
            for module in modules:
                if is_filepath and name == module.realpath:
                    return module
                elif name == module.name and byname:
                    return module
                elif name == module.fullname:
                    return module
                elif name == module.name and module.default:
                    return module
        return None

    def display(self, what, terse=False):
        if what == 'available':
            return self.display_available(terse=terse)
        if what == 'loaded':
            return self.display_loaded(terse=terse)

    def display_available(self, terse=False):
        height, width = get_console_dims()

        for (directory, dir_modules) in self._available_modules.items():
            modules = []
            for m in dir_modules:
                if m.hidden:
                    continue
                name = m.fullname
                if not terse:
                    if m.default and m.loaded:
                        name += ' (D, ' + colors.YELLOW + 'L' + colors.ENDC + ')'
                    elif m.default:
                        name += ' (D)'
                    elif m.loaded:
                        name += ' (' + colors.YELLOW + 'L' + colors.ENDC + ')'
                modules.append(name)

            if terse:
                log_message(directory + ':')
                if not modules:
                    continue
                log_message('\n'.join(x.strip() for x in modules))
            else:
                log_message('{0:-^{1}}'.format(directory, width))
                if not modules:
                    s = colors.RED+'(None)'+colors.ENDC
                    log_message('{0: ^{1}}'.format(s, width))
                    continue
                log_message(format_text_to_cols(modules, width) + '\n')

    def display_loaded(self, terse=False):
        """Print loaded modules to the console"""
        height, width = get_console_dims()
        loaded = [m.fullname for (d, ms) in self._available_modules.items()
                  for m in ms if m.loaded]
        if not loaded:
            log_message('No modulefiles currently loaded.')
            return

        log_message('\nCurrently loaded modulefiles:')
        modules = ['{0})&{1}'.format(i+1, m)
                   for (i, m) in enumerate(loaded)]
        if terse:
            log_message('\n'.join(modules).replace('&', ' '))
        else:
            string = format_text_to_cols(modules, width)
            log_message(string.replace('&', ' ')+'\n')


available_modules = AvailableModules()
