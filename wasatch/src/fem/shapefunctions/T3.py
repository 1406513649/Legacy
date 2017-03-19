import numpy as np
import src.base.consts as consts
from src.fem.shapefunctions.prototype import ShapeFunctionPrototype
from src.fem.shapefunctions.B2 import ShapeFunction_Bar2


class ShapeFunction_Tri3(ShapeFunctionPrototype):
    """Element function for linear CST element defined in [1]

    Notes
    -----
    Node and element face numbering


            2
            |\
       [2]  |  \  [1]
            |    \
            0-----1
              [0]

    References
    ----------
    1. Taylor & Hughes (1981), p.49

    """

    name = "TRIANGLE3"
    canreduce = True
    dim, nnodes = 2, 3
    ngauss = 1
    cornernodes = np.array([0, 1, 2])
    facenodes = np.array([[0, 1], [1, 2], [2, 0]])
    gauss_coords = np.array([[1., 1]], dtype=np.float64) / 3.
    gauss_weights = np.array([.5], dtype=np.float64)
    _topomap = {"ILO": 2, "IHI": 1, "JLO": 0, "JHI": 2}
    bndry = ShapeFunction_Bar2()

    """
    mass stuff
    if False:
        # mass stuff for explicit
        nmass = 4
        # mass gauss coords
        return np.array([[1. / 3., 1. / 3.],
                         [.6, .2],
                         [.2, .6],
                         [.2, .2]], dtype=np.float64)
        # mass weights
        return np.array([-27, 25, 25, 25], dtype=np.float64) / 96.
    """

    def calc_shape(self, lcoord):
        x, y = lcoord[:2]
        return np.array([x, y, 1. - x - y])

    def calc_shape_deriv(self, lcoord):
        return np.array([[1, 0, -1],
                         [0, 1, -1]], dtype=np.float64)
