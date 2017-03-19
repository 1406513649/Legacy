from available_modules import available_modules
from moduleio import ModuleError
def prereq(name, other):
    if other not in available_modules:
        raise ModuleError('Module {0} requires that '
                          '{1} be loaded'.format(name, other))
