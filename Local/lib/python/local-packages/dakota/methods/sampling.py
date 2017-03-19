from ._method import Method

class SamplingMethod(Method):
    def __init__(self, id_method, model_pointer, 
                 backfill=False, fixed_seed=False,
                 max_iterations=None, convergence_tolerance=None,
                 samples=None, seed=None):
        super(SamplingMethod, self).__init__(id_method, model_pointer)

        self._backfill = backfill
        self._fixed_seed = fixed_seed
        self._max_iterations = max_iterations
        self._convergence_tolerance = convergence_tolerance
        self._samples = samples
        self._seed = seed
        self._sample_type = None

    @property
    def backfill(self):
        return self._backfill

    @backfill.setter
    def backfill(self, arg):
        self._backfill = bool(arg)

    @property
    def fixed_seed(self):
        return self._fixed_seed

    @fixed_seed.setter
    def fixed_seed(self, arg):
        self._fixed_seed = bool(arg)

    @property
    def max_iterations(self):
        return self._max_iterations

    @max_iterations.setter
    def max_iterations(self, arg):
        self._max_iterations = int(arg)

    @property
    def convergence_tolerance(self):
        return self._convergence_tolerance

    @convergence_tolerance.setter
    def convergence_tolerance(self, arg):
        self._convergence_tolerance = float(arg)

    @property
    def samples(self):
        return self._samples

    @samples.setter
    def samples(self, arg):
        self._samples = int(arg)

    @property
    def seed(self):
        return self._seed

    @seed.setter
    def seed(self, arg):
        self._seed = int(arg)

    @property
    def sample_type(self):
        return self._sample_type

    @sample_type.setter
    def sample_type(self, sample_type):
        valid_sample_types = ('random', 'lhs')
        if sample_type.lower() not in valid_sample_types:
            raise ValueError(sample_type)
        self._sample_type = sample_type.lower()

    def as_string(self):
        s = []
        if self.samples:
            s.append('samples {0}'.format(self.samples))

        if self.seed:
            s.append('seed {0}'.format(self.seed))

        if self.backfill:
            s.append('backfill')

        if self.fixed_seed:
            s.append('fixed_seed')

        if self.max_iterations:
            s.append('max_iterations {0}'.format(self.max_iterations))
        
        if self.sample_type:
            s.append('sample_type {0}'.format(self.sample_type))

        s1 = super(SamplingMethod, self).as_string()
        return s1 + '\n  sampling\n    ' + '\n    '.join(s)
