
class Model:

    def __init__(self, id_model, variables_pointer, responses_pointer,
                 hierarchical_tagging=None):
        self.id_model = id_model
        self.variables_pointer = variables_pointer
        self.responses_pointer = responses_pointer
        self.hierarchical_tagging = hierarchical_tagging

    def as_string(self):
        s = ['id_model = {0!r}'.format(self.id_model)]
        s.append('variables_pointer = {0!r}'.format(
            self.variables_pointer.id_variables))
        s.append('responses_pointer = {0!r}'.format(
            self.responses_pointer.id_responses))
        return 'model\n  ' + '\n  '.join(s)
