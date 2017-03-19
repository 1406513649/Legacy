from numpy import array, zeros, float64

from elem_base import ContinuumElement
from gl_quadrature import ShapefunctionPrototype, IntegrationProperties
import mesh.geom as geom

class TRIE3(ContinuumElement):
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
    ndi = 3
    nshr = 1
    name = "TRIE3"
    num_node = 3
    num_coord = 2
    num_dof_per_node = 2
    type = geom.get_elem_type(num_coord, num_node)
    cp = geom.elem_center_coord(num_coord, num_node)
    xp = geom.elem_corner_coord(num_coord, num_node)

    def __init__(self):

        # integration scheme for this element
        self.integration = IntegrationProperties(self.num_coord, self.num_node)
        self.shape = ShapefunctionPrototype(self.num_coord, self.num_node)

        # element boundary properties
        self.num_face_nodes = geom.num_face_nodes(self.num_coord, self.num_node)
        args = (self.num_coord-1, self.num_face_nodes)
        self.bndry = ShapefunctionPrototype(*args)
        self.bndry.integration = IntegrationProperties(*args)
        self.thickness = 1.

    @staticmethod
    def b_matrix(shg, shgbar=None, **kwargs):
        """Assemble and return the B matrix"""
        B = zeros((4, 6))
        B[0, 0::2] = shg[0, :]
        B[1, 1::2] = shg[1, :]
        B[3, 0::2] = shg[1, :]
        B[3, 1::2] = shg[0, :]
        return B

    @classmethod
    def volume(cls, coords):
        return geom.elem_volume(cls.num_coord, cls.num_node, coords, cls.thickness)
