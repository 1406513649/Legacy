__all__ = ['Variables']

from collections import OrderedDict
from itertools import groupby

from ._variable import *
from ..common_tools import *

class DuplicateVariableError(Exception):
    pass


class Variables(OrderedDict):
    
    def __init__(self, id_variables):
        self.id_variables = id_variables
        self.ucm = {}

    def __setitem__(self, key, value):
        if key in self:
            raise DuplicateVariableError('{0!r}'.format(key))
        super(Variables, self).__setitem__(key, value)

    def __getitem__(self, key):
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val

    def __contains__(self, arg):
        try:
            return super(Variables, self).__contains__(arg.descriptor)
        except AttributeError:
            return super(Variables, self).__contains__(arg)

    def put(self, variable):
        self[variable.descriptor] = variable
        return variable

    def get(self, key, default=None):
        try:
            key_low = key.descriptor.lower()
        except AttributeError:
            key_low = key.lower()
        for (k, v) in self.items():
            if k.lower() == key_low:
                return v
        return default

    def groupby_type(self):
        groups = []
        for (key, group) in groupby(self.keys(), key=lambda x: self[x].title):
            groups.append([self[x] for x in group])
        return groups
            
    def as_string(self, indent='  '):
        """Form the Dakota input specification"""
        s = []
        descriptors = []
        for group in self.groupby_type():
            s.append('{0}{1} = {2}'.format(indent, group[0].title, len(group)))
            table = []
            descriptors.extend([getattr(x, 'descriptor') for x in group])
            for attr in group[0].attrs_to_write:
                values = [getattr(x, attr) for x in group]
                if all(x is None for x in values):
                    continue
                if any(is_stringlike(x) for x in values):
                    values = [fmt_string_value(x, 1) for x in values]
                else:
                    values = [fmt_string_value(x) for x in values]
                key = attr if attr == 'initial_point' else attr + 's'
                table.append([key] + values)

            s.append(format_table(table)+'\n')
            continue

        s1 = 'variables\n'
        s2 = '{0}id_variables = {1!r}\n'.format(indent, self.id_variables)
        s3 = '\n'.join(s)

        s = s1 + s2 + s3

        # uncertain correlation matrix
        if self.ucm:
            s4 = []
            n = len(descriptors)
            m = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
            for (key, corr) in self.ucm.items():
                var_1, var_2 = key
                i, j = descriptors.index(var_1), descriptors.index(var_2)
                m[i][j] = m[j][i] = corr
            s4.append(indent + 'uncertain_correlation_matrix')
            for row in m:
                s4.append(2*indent + ' '.join('{0}'.format(x) for x in row))

            s += '\n' + '\n'.join(s4)

        return s

    def uncertain_correlation_matrix(self, var_1, var_2, corr):
        if var_1 not in self:
            raise KeyError('{0!r}'.format(var_1))
        if var_2 not in self:
            raise KeyError('{0!r}'.format(var_2))
        self.ucm[(var_1, var_2)] = corr

    def correlated_vars(self, var_1, var_2, corr):
        return self.uncertain_correlation_matrix(var_1, var_2, corr)

    def NormalUncertain(self, *args, **kwargs):
        return self.put(NormalUncertain(*args, **kwargs))

    def UniformUncertain(self, *args, **kwargs):
        return self.put(UniformUncertain(*args, **kwargs))

    def ContinuousDesign(self, *args, **kwargs):
        return self.put(ContinuousDesign(*args, **kwargs))


def format_table(table, indent='  '):
    table_fmt = []
    fn = round_up_to_odd
    nr = len(table)
    nc = len(table[0]) - 1 
    mx_key = fn(max([len(row[0]) for row in table]))
    mx_cols = [fn(max([len(row[i+1]) for row in table])) for i in range(nc)]
    for row in table:
        p_indent = ' ' * (mx_key - len(row[0]))
        key = '{0}{1}{2} ='.format(indent, row[0], p_indent)
        line = ['{0:^{1}}'.format(x, mx_cols[i]) for (i,x) in enumerate(row[1:])]
        table_fmt.append(' '.join([key] + line))
    return '\n'.join(indent+x for x in table_fmt).rstrip()
