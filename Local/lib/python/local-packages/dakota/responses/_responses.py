
class Responses:
    def __init__(self, id_responses):
        self.id_responses = id_responses
        self.gradients = None
        self.hessians = None
        self.responses = []

    def response(self, name):
        self.responses.append(name)

    def as_string(self):
        s = ['id_responses = {0!r}'.format(self.id_responses)]
        s.append('response_functions = {0}'.format(len(self.responses)))
        desc = ' '.join('{0!r}'.format(x) for x in self.responses)
        s.append('response_descriptors = {0}'.format(desc))

        if self.gradients is None:
            s.append('no_gradients')

        if self.hessians is None:
            s.append('no_hessians')

        return 'responses\n  ' + '\n  '.join(s)

