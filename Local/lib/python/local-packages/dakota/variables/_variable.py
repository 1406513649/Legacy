__all__ = ['NormalUncertain', 'UniformUncertain', 'ContinuousDesign']


class Variable(object):
    """Base class for variable objects"""
    def __init__(self, title, descriptor, *variable_attrs):
        self.title = title
        self.descriptor = descriptor
        self.attrs_to_write = ['descriptor']
        for (name, value) in variable_attrs:
            setattr(self, name, value)
            self.attrs_to_write.append(name)
        self._check_bounds()

    def __repr__(self):
        return self.__str__()

    def _check_bounds(self):
        def get_attr(attr):
            return getattr(self, attr, None)
        key = self.descriptor
        mean = get_attr('mean')
        lb = get_attr('lower_bound')  
        ub = get_attr('upper_bound')  
        ip = get_attr('initial_point')  

        if lb is not None:
            err_message = '{0} of {1} less than lower_bound'
            if mean is not None and mean < lb:
                raise ValueError(err_message.format('mean', key))
            if ub is not None and ub < lb:
                raise ValueError(err_message.format('upper_bound', key))
            if ip is not None and ip < lb:
                raise ValueError(err_message.format('initial_point', key))

        if ub is not None:
            err_message = '{0} of {1} greater than upper_bound'
            if mean is not None and mean > ub:
                raise ValueError(err_message.format('mean', key))
            if lb is not None and lb > ub:
                raise ValueError(err_message.format('lower_bound', key))
            if ip is not None and ip > ub:
                raise ValueError(err_message.format('initial_point', key))

        if ip is not None:
            err_message = 'initial_point of {0} {1} than {2}'
            if lb is not None and ip < lb:
                msg = err_message.format(key, 'less', 'lower_bound')
                raise ValueError(msg)
            if ub is not None and ip > lb:
                msg = err_message.format(key, 'greater', 'upper_bound')
                raise ValueError(msg)

        return None


class NormalUncertain(Variable):
    def __init__(self, descriptor, mean, std_deviation, lower_bound=None,
            upper_bound=None, initial_point=None):
        super(NormalUncertain, self).__init__('normal_uncertain', descriptor,
                ('mean', mean), ('std_deviation', std_deviation),
                ('lower_bound', lower_bound), ('upper_bound', upper_bound),
                ('initial_point', initial_point))
    def __str__(self):
        string = 'NormalUncertain(mean={0}, std_deviation={1})'
        return string.format(self.mean, self.std_deviation)


class UniformUncertain(Variable):
    def __init__(self, descriptor, mean, lower_bound, upper_bound,
            initial_point=None):
        super(UniformUncertain, self).__init__('uniform_uncertain', 
                descriptor, ('mean', mean), ('lower_bound', lower_bound),
                ('upper_bound', upper_bound), ('initial_point', initial_point))
    def __str__(self):
        string = 'UniformUncertain(mean={0}, bounds=({1}, {2}))'
        return string.format(self.mean, self.lower_bound, self.upper_bound)


class ContinuousDesign(Variable):
    def __init__(self, descriptor, initial_point, 
            lower_bound, upper_bound):
        super(ContinuousDesign, self).__init__('continuous_design',
                descriptor, ('initial_point', initial_point),
                ('lower_bound', lower_bound),
                ('upper_bound', upper_bound))
    def __str__(self):
        string = 'UniformUncertain(initial_point={0}, bounds=({1}, {2}))'
        return string.format(self.initial_point, 
                             self.lower_bound, self.upper_bound)
