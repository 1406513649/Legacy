from tools.constants import ROOT3
from numpy import array, float64

from elem import ContinuumElement
import mesh.geom as geom

class BAR2(ContinuumElement):
    """2-node, isoparametric element

    Notes
    -----
    Node and element face numbering

            0-------1
               [0]

    """
    ndi = 1
    nshr = 0
    name = "BAR2"
    num_node = 2
    num_coord = 1
    num_dof_per_node = 1
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
