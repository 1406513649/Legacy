import numpy as np
from numpy import dot, array, zeros, float64

from elem_reduced import ContinuumElementR
from gl_quadrature import ShapefunctionPrototype, IntegrationProperties
import mesh.geom as geom

class QE4RI(ContinuumElementR):
    """4-node, isoparametric, plane strain element

    Notes
    -----
    Node and element face numbering

               [2]
            3-------2
            |       |
       [3]  |       | [1]
            |       |
            0-------1
               [0]

    """
    ndi = 3
    nshr = 1
    name = "QE4RI"
    num_node = 4
    num_coord = 2
    num_dof_per_node = 2
    type = geom.get_elem_type(num_coord, num_node)
    cp = geom.elem_center_coord(num_coord, num_node)
    xp = geom.elem_corner_coord(num_coord, num_node)

    def __init__(self):

        # integration scheme for this element
        self.integration = IntegrationProperties(self.num_coord, self.num_node,
                                                 reduced=True)
        self.shape = ShapefunctionPrototype(self.num_coord, self.num_node)

        # element boundary properties
        self.num_face_nodes = geom.num_face_nodes(self.num_coord, self.num_node)
        args = (self.num_coord-1, self.num_face_nodes)
        self.bndry = ShapefunctionPrototype(*args)
        self.bndry.integration = IntegrationProperties(*args)
        self.thickness = 1.

    def b_matrix(self, shg, shgbar=None, **kwargs):
        """Assemble and return the B matrix"""
        B = zeros((self.ndi+self.nshr, self.num_node * self.num_dof_per_node))
        B[0, 0::2] = shg[0, :]
        B[1, 1::2] = shg[1, :]
        B[3, 0::2] = shg[1, :]
        B[3, 1::2] = shg[0, :]

        if shgbar is None:
            return B

        # mean dilatational formulation
        for a in range(self.num_node):
            i = 2 * a
            j = i + 1

            bb1 = (shgbar[0, a] - shg[0, a]) / 2.
            bb2 = (shgbar[1, a] - shg[1, a]) / 2.

            B[0, i:i+2] += [bb1, bb2]
            B[1, i:i+2] += [bb1, bb2]

        return B

    @classmethod
    def volume(cls, coords):
        return geom.elem_volume(cls.num_coord, cls.num_node, coords, cls.thickness)

    @property
    def hgpoints(self):
        # hourglass points
        return array([[0., 0.]])

    @property
    def hgvec(self):
        # hourglass vector
        return array([[1, -1, 1, -1]], dtype=np.float64)
