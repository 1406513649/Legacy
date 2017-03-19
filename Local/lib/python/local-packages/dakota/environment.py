from os.path import splitext

from .utils import *

class TabularData:
    def __init__(self, name='dakota'):
        try:
            name, ext = splitext(name)
        except ValueError:
            ext = '.dat'
        if not ext:
            ext = '.dat'
        self.name = name
        self.tabular_data_file = name + ext
        self.annotated = True
        self._custom_annotated = None
        self.freeform = False

    @property
    def custom_annotated(self):
        return self._custom_annotated

    @custom_annotated.setter
    def custom_annotated(self, opts):
        if is_stringlike(opts):
            opts = (opts,)
        self.annotated = False
        self.freeform = False
        valid_opts = ('header', 'eval_id', 'interface_id')
        self._custom_annotated = []
        for opt in opts:
            if opt.lower() not in valid_opts:
                raise ValueError('{0!r} not a valid tabular_data option')
            if opt not in self._custom_annotated:
                self._custom_annotated.append(opt)

    def as_string(self, indent='  '):
        s = [indent + 'tabular_data']
        if self.annotated:
            s.append(2*indent + 'annotated')
        elif self.freeform:
            s.append(2*indent + 'freeform')
        elif self.custom_annotated:
            a = ' '.join(self.custom_annotated)
            if a:
                s.append(2*indent + 'custom_annotated ' + a)
        s.append(2*indent + 
                'tabular_data_file = {0!r}'.format(self.tabular_data_file))
        return '\n'.join(s)


class Environment:
    def __init__(self, name=None):
        self.name = name
        self._check = False
        self._graphics = None

        self._output_file = None
        self._error_file = None
        if self.name is None:
            self._write_restart = None
        else:
            self._write_restart = self.name + '.rst'

        self._tabular_data = None
        self._output_precision = 10
        self._top_method_pointer = None
        self._results_output = None

    @property
    def check(self):
        return self._check

    @check.setter
    def check(self, arg):
        self._check = bool(arg)

    @property
    def graphics(self):
        return self._graphics

    @graphics.setter
    def graphics(self, arg):
        self._graphics = bool(arg)

    @property
    def output_file(self):
        return self._output_file

    @output_file.setter
    def output_file(self, filename):
        if not is_stringlike(filename):
            if self.name is None:
                filename = 'dakota.out'
            else:
                filename = self.name + '.out'
        self._output_file = filename

    @property
    def error_file(self):
        return self._error_file

    @error_file.setter
    def error_file(self, filename):
        if not is_stringlike(filename):
            if self.name is None:
                filename = 'dakota.err'
            else:
                filename = self.name + '.err'
        self._error_file = filename

    @property
    def write_restart(self):
        if self._write_restart is None:
            return 'dakota.rst'
        return self._write_restart

    @write_restart.setter
    def write_restart(self, filename):
        if not is_stringlike(filename):
            if self.name is None:
                filename = 'dakota.rst'
            else:
                filename = self.name + '.rst'
        if not filename.endswith('.rst'):
            filename += '.rst'
        self._write_restart = filename

    @property
    def output_precision(self):
        return self._output_precision

    @output_precision.setter
    def output_precision(self, _int):
        self._output_precision = int(_int)

    @property
    def top_method_pointer(self):
        return self._top_method_pointer

    @top_method_pointer.setter
    def top_method_pointer(self, method):
        self._top_method_pointer = method

    @property
    def results_output(self):
        return self._results_output

    @results_output.setter
    def results_output(self, basename):
        if is_stringlike(basename):
            self._results_output = basename
        else:
            if self.name is None:
                self._results_output = 'dakota_results'
            else:
                self._results_output = self.name + '_results'

    @property
    def tabular_data(self):
        return self._tabular_data

    @tabular_data.setter
    def tabular_data(self, name):
        if not is_stringlike(name):
            if not bool(name):
                return
            if self.name is None:
                name = 'dakota'
            else:
                name = self.name
        self._tabular_data = TabularData(name=name)

    def as_string(self):
        s = ['environment']
        if self.check:
            s.append('  check')
        if self.output_file:
            s.append('  output_file = {0!r}'.format(self.output_file))
        if self.error_file:
            s.append('  error_file = {0!r}'.format(self.error_file))
        s.append('  write_restart = {0!r}'.format(self.write_restart))
        if self.graphics:
            s.append('  graphics')
        if self.tabular_data:
            s.append(self.tabular_data.as_string(indent='  '))
        if self.results_output:
            s.append('  results_output')
            s.append('    results_output_file = {0!r}'.format(
                self.results_output))
        if self.top_method_pointer:
            s.append('  top_method_pointer = {0!r}'.format(
                self.top_method_pointer.id_method))

        return '\n'.join(s)
