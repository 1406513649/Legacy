import numpy as np

from material.material import MaterialModel
from material.completion import EC_BULK, EC_SHEAR
from tools.datastructs import ARRAY, SYMTEN

class Elastic(MaterialModel):
    """Plane strain elastic material"""
    name = "elastic"
    param_names = ("E", "NU")
    properties = [EC_BULK, EC_SHEAR]

    def setup(self):
        self.E, self.v = self.parameters
        self.shear_modulus = self.E / 2. / (1. + self.v)
        self.bulk_modulus = self.E / 3. / (1. - 2. * self.v)
        self.register_variable("STRESS", SYMTEN)
        self.register_variable("DSTRAIN", SYMTEN)
        #self.register_variable("STATEV", ARRAY, keys=["SV1", "SV2"], ivals=(1, 2))

    @property
    def C(self):
        """Tangent stiffness (plane strain)"""
        fac = self.E / (1. + self.v) / (1. - 2. * self.v)
        c11 = fac * (1. - self.v)
        c12 = fac * self.v
        c44 = fac * (1. - 2. * self.v) / 2.
        C = np.array([[c11, c12, c12, 0,   0,   0  ],
                      [c12, c11, c12, 0,   0,   0  ],
                      [c12, c12, c11, 0,   0,   0  ],
                      [0,   0,   0,   c44, 0,   0  ],
                      [0,   0,   0,   0,   c44, 0  ],
                      [0,   0,   0,   0,   0,   c44]], dtype=np.float64)
        return C

    def update_state(self, time, dtime, temp, dtemp, energy, rho, F0, F,
        strain, dstrain, elec_field, user_field, ndi, nshr, ntens, coords,
        elem_num, gauss_point, step_num, stress, ddsdde, xtra):

        if nshr == 1:
            # Modify the stiffness for 2D according to:
            # 1) Plane strain: Remove rows and columns of the stiffness
            #    corresponding to the plane of zero strain
            # 2) Plane stress: Invert the stiffness and remove the rows
            #    and columns of the compliance corresponding the plane of
            #    zero stress.
            if ndi == 2:
                # plane stress
                # Invert the stiffness to get the compliance
                idx = [[[0], [1], [3]], [0, 1, 3]]
                ddsdde[:] = np.linalg.inv(np.linalg.inv(self.C)[idx])
            elif ndi == 3:
                # plane strain
                idx = [[[0], [1], [2], [3]], [0, 1, 2, 3]]
                ddsdde[:] = self.C[idx]
            else:
                logger.raise_error("unknown ndi, nshr combo")
        else:
            ddsdde[:] = self.C

        dstress = np.dot(ddsdde, dstrain)
        stress[:ntens] += dstress

        return
