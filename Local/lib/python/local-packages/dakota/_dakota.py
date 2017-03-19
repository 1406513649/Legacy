from collections import OrderedDict

from .environment import Environment
from .methods import Method
from .models import Model
from .variables import Variables
from .responses import Responses
from .interfaces import Interfaces
from .utils import *

class DakotaModel:
    def __init__(self, name):
        self.name = name
        self.methods = Repository()
        self.models = Repository()
        self.variables = []
        self.responses = []
        self.interfaces = []

        self.environment = Environment(name=name)

    def check(self):
        self.environment.check = 1
        self.run()

    def run(self):
        print(self.as_string())

    @property
    def graphics(self):
        return self.environment.graphics

    @graphics.setter
    def graphics(self, arg):
        self.environment.graphics = arg

    @property
    def output_file(self):
        return self.environment.output_file

    @output_file.setter
    def output_file(self, filename):
        if not is_stringlike(filename):
            filename = self.name + '.out'
        self.environment.output_file = filename

    @property
    def error_file(self):
        return self.environment.error_file

    @error_file.setter
    def error_file(self, filename):
        if not is_stringlike(filename):
            filename = self.name + '.err'
        self.environment.error_file = filename

    @property
    def write_restart(self):
        return self.environment.write_restart

    @write_restart.setter
    def write_restart(self, filename):
        if not is_stringlike(filename):
            filename = self.name + '.rst'
        self.environment.write_restart = filename

    @property
    def top_method_pointer(self):
        return self.environment.top_method_pointer

    @top_method_pointer.setter
    def top_method_pointer(self, method):
        if method not in self.methods:
            raise ValueError('Unknown top method pointer')
        self.environment.top_method_pointer = self.methods[method]

    @property
    def results_output(self):
        return self.environment.results_output

    @results_output.setter
    def results_output(self, basename):
        if is_stringlike(basename):
            self.environment.results_output = basename
        else:
            self.environment.results_output = self.name + '_results'

    @property
    def tabular_data(self):
        return self.environment.tabular_data

    @tabular_data.setter
    def tabular_data(self, name):
        if not is_stringlike(name):
            if not bool(name):
                return
            name = self.name
        self.environment.tabular_data = name

    def Method(self, method, id_method=None, model_pointer=None, **kwargs):

        if id_method is None:
            n = len(self.methods) + 1
            while 1:
                id_method = self.name + '_method-{0}'.format(n)
                if id_method not in self.methods:
                    break
                n += 1

        if id_method in self.methods:
            raise ValueError('Duplicate method name {0!r}'.format(id_method))

        if model_pointer is None:
            model_pointer = self.models[-1]

        method = Method(method, id_method, model_pointer, **kwargs)
        self.methods.append(method)

        return method

    def Model(self, id_model=None, variables_pointer=None,
            responses_pointer=None, hierarchical_tagging=None):

        if id_model is None:
            n = len(self.models) + 1
            while 1:
                id_model = self.name + '_method-{0}'.format(n)
                if id_model not in self.models:
                    break
                n += 1

        if id_model in self.models:
            raise ValueError('Duplicate model name {0!r}'.format(id_model))

        if variables_pointer is None:
            variables_pointer = self.variables[-1]

        if responses_pointer is None:
            responses_pointer = self.responses[-1]

        model = Model(id_model, variables_pointer, responses_pointer,
                hierarchical_tagging=hierarchical_tagging)

        self.models.append(model)

        return model

    def Variables(self, id_variables):
        v = Variables(id_variables)
        self.variables.append(v)
        return v

    def Responses(self, id_responses):
        r = Responses(id_responses)
        self.responses.append(r)
        return r

    def Interfaces(self, id_interface):
        i = Interfaces(id_interface)
        self.interfaces.append(i)
        return i
        
    def as_string(self):
        if not self.methods:
            raise ValueError('At least one method required')

        cp = '# ' + '-'*76 + ' #'
        s = [cp, '# --- Dakota specification file', cp]
        s.append(self.environment.as_string())
        s.append('')

        s.extend([cp, '# --- Models', cp])
        for model in self.models:
            s.append(model.as_string())
            s.append('')

        s.extend([cp, '# --- Methods', cp])
        for method in self.methods:
            s.append(method.as_string())
            s.append('')

        s.extend([cp, '# --- Variables', cp])
        for v in self.variables:
            s.append(v.as_string())
            s.append('')

        s.extend([cp, '# --- Responses', cp])
        for r in self.responses:
            s.append(r.as_string())
            s.append('')

        s.extend([cp, '# --- Interfaces', cp])
        for i in self.interfaces:
            s.append(i.as_string())
            s.append('')
        return '\n'.join(s)

    def write_input(self):
        with open(self.name + '.in', 'w') as fh:
            fh.write(self.as_string())
