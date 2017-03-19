from numpy import array, zeros, float64

from elem_base import ContinuumElement
from gl_quadrature import ShapefunctionPrototype, IntegrationProperties
import mesh.geom as geom

class HEX8RI(ContinuumElement):
    """Trilinear hex element

    Notes
    -----
    Integration points in parentheses

          7---------------6
         /|(7)        (6)/|
        / |             / |
       /  |            /  |
      /   |           /   |
     / (4)|       (5)/    |
    4---------------5     |
    |     |         |     |
    |     3---------|-----2
    |    / (3)      | (2)/
    |   /           |   /
    |  /            |  /
    | /             | /
    |/ (0)       (1)|/
    0---------------1

    """
    ndi = 3
    nshr = 3
    name = "HEX8RI"
    num_node = 8
    num_coord = 3
    num_dof_per_node = 3
    type = geom.get_elem_type(num_coord, num_node)
    cp = geom.elem_center_coord(num_coord, num_node)
    xp = geom.elem_corner_coord(num_coord, num_node)

    def __init__(self):

        # integration scheme for this element
        self.integration = IntegrationProperties(self.num_coord,
                                                 self.num_node, reduced=True)
        self.shape = ShapefunctionPrototype(self.num_coord, self.num_node)

        # element boundary properties
        self.num_face_nodes = geom.num_face_nodes(self.num_coord, self.num_node)
        args = (self.num_coord-1, self.num_face_nodes)
        self.bndry = ShapefunctionPrototype(*args)
        self.bndry.integration = IntegrationProperties(*args)

    def b_matrix(self, shg, shgbar=None, **kwargs):
        B = zeros((6, 24))
        B[0, 0::3] = shg[0, :]
        B[1, 1::3] = shg[1, :]
        B[2, 2::3] = shg[2, :]

        B[3, 0::3] = shg[1, :]
        B[3, 1::3] = shg[0, :]

        B[4, 1::3] = shg[2, :]
        B[4, 2::3] = shg[1, :]

        B[5, 0::3] = shg[2, :]
        B[5, 2::3] = shg[0, :]

        return B

    @classmethod
    def volume(cls, coords):
        return geom.elem_volume(cls.num_coord, cls.num_node, coords)
