from numpy import array, dot, concatenate, sum as asum, float64, zeros
from numpy.linalg import inv, det as determinant

from elem_incompat import ContinuumElementI
from gl_quadrature import IntegrationProperties, ShapefunctionPrototype
import mesh.geom as geom

class QE4IM(ContinuumElementI):
    """4-node, isoparametric, plane strain element, incompatible modes

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
    name = "QE4IM"
    num_node = 4
    num_coord = 2
    num_dof_per_node = 2
    num_incompat_modes = 2
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

    def b_matrix(self, shg, shgbar=None, lcoords=None, coords=None, det=None,
                 disp=0, **kwargs):
        """Assemble and return the B matrix"""
        B = zeros((self.ndi+self.nshr, self.num_node * self.num_dof_per_node))
        B[0, 0::2] = shg[0, :]
        B[1, 1::2] = shg[1, :]
        B[3, 0::2] = shg[1, :]
        B[3, 1::2] = shg[0, :]

        if not disp:
            return B

        # Algorithm in
        # The Finite Element Method: Its Basis and Fundamentals
        # By Olek C Zienkiewicz, Robert L Taylor, J.Z. Zhu
        # Jacobian at element centroid
        dNdxi = self.shape.grad([0., 0.])
        dxdxi = dot(dNdxi, coords)
        J0 = inv(dxdxi)
        dt0 = determinant(dxdxi)

        xi, eta = lcoords
        dNdxi = array([[-2. * xi, 0.], [0., -2. * eta]])
        dNdx = dt0 / det * dot(J0, dNdxi)

        G1 = array([[dNdx[0, 0],  0],
                    [0,  dNdx[0, 1]],
                    [0, 0],
                    [dNdx[0, 1], dNdx[0, 0]]])

        G2 = array([[dNdx[1, 0],  0],
                    [0,  dNdx[1, 1]],
                    [0,  0],
                    [dNdx[1, 1], dNdx[1, 0]]])
        G = concatenate((G1, G2), axis=1)
        return B, G

        # Algorithm in Taylor's original paper and
        # The Finite Element Method: Linear Static and Dynamic
        # Finite Element Analysis
        # By Thomas J. R. Hughe
        xi = self.gauss_coords
        n = self.num_gauss
        dxdxi = asum([coords[i, 0] * xi[i, 0] for i in range(n)])
        dxdeta = asum([coords[i, 0] * xi[i, 1] for i in range(n)])
        dydxi = asum([coords[i, 1] * xi[i, 0] for i in range(n)])
        dydeta = asum([coords[i, 1] * xi[i, 1] for i in range(n)])

        xi, eta = lcoords
        G1 = array([[-xi * dydeta, 0],
                    [0, xi * dxdeta],
                    [0, 0],
                    [xi * dxdeta, -xi * dydeta]])
        G2 = array([[-eta * dydxi, 0.],
                    [0, eta * dxdxi],
                    [0, 0],
                    [eta * dxdxi, -eta * dydxi]])
        G = 2. / det * concatenate((G1, G2), axis=1)
        return B, G

    @classmethod
    def volume(cls, coords):
        return geom.elem_volume(cls.num_coord, cls.num_node, coords, cls.thickness)
