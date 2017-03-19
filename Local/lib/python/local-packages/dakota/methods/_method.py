
class Method(object):
    def __init__(self, id_method, model_pointer):
        self.id_method = id_method
        self.model_pointer = model_pointer

        self._output = 'normal'
        self._probability_levels = {}

    @property
    def output(self):
        return self._output

    @output.setter
    def output(self, level):
        valid_levels = ('debug', 'verbose', 'normal', 'quiet', 'silent')
        if level not in valid_levels:
            raise ValueError('Expected level to be one of '
                    '{0}'.format(','.join(valid_levels)))
        self._output = level.lower()

    def probability_levels(self, response, levels):
        self._probability_levels[responses] = levels

    def as_string(self):
        s = ['id_method = {0!r}'.format(self.id_method)]
        s.append('model_pointer = {0!r}'.format(self.model_pointer.id_model))
        s.append('output ' + self.output)
        return 'method\n  ' + '\n  '.join(s)

    def Sampling(self, id
