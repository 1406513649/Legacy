import numpy as np
from tools.logger import ConsoleLogger as logger
from tools.datastructs import SYMTEN, ARRAY, SCALAR, Variable
from tools.errors import AFEPYError


class MetaClass(type):
    def __call__(cls, parameters):
        obj = type.__call__(cls)
        obj.post__init__(parameters)
        return obj

class MaterialModel(object):
    """Base material class"""
    matmodel = 1
    num_statev = 0
    __metaclass__ = MetaClass

    def __call__(self, time, dtime, temp, dtemp, energy, F0, F,
                 strain, dstrain, elec_field, user_field, ndi, nshr, ntens,
                 coords, elem_id, npt, kstep, stress, statev):
        D = np.zeros((ntens, ntens))
        self.update_state(time, dtime, temp, dtemp, energy, self.density, F0, F,
                          strain, dstrain, elec_field, user_field,
                          ndi, nshr, ntens, coords, elem_id, npt, kstep,
                          stress, D, statev)

        return D

    @property
    def hourglass_stiffness(self):
        return .01 * self.shear_modulus

    @property
    def param_map(self):
        return dict([(a.upper(), i) for (i, a) in enumerate(self.param_names)])

    @classmethod
    def parse_parameters(cls, param_dict):
        params = np.zeros(len(cls.param_names))
        param_map = dict([(a.upper(), i) for (i, a) in enumerate(cls.param_names)])
        for (key, val) in param_dict.items():
            i = param_map.get(key.upper())
            if i is None:
                logger.warn("{0}: invalid parameter for model "
                            "{1}".format(key, self.name))
                continue
            params[i] = val
        return params

    @property
    def variables(self):
        if getattr(self, "_vars", None) is None:
            self._vars = []
        return self._vars

    def register_variable(self, name, type, keys=None, ivals=None):
        if name in [v.name for v in self.variables]:
            raise AFEPYError("duplicate element variable {0}".format(name))
        self.variables.append(Variable(name, type, keys, ivals))

    def update_state(self, *args, **kwargs):
        raise NotImplementedError("update_state must be defined by individual "
                                  "materials and not the base class")

    def setup(self, *args, **kwargs):
        pass

    def post__init__(self, parameters):
        self.parameters = np.array(parameters)
        self.setup()
