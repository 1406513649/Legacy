from numpy import zeros, int32, array, float64
from numpy.linalg import det

def get_elem_type(num_dim, num_nodes_per_elem):
    """Get the element type by dimension and number of nodes per element

    """
    d = {(2, 3): "TRI3", (2, 6): "TRI6",
         (2, 4): "QUAD4", (2, 8): "QUAD8",
         (3, 4): "TET4", (3, 10): "TET10",
         (3, 8): "HEX8", (3, 20): "HEX20"}
    return d[(num_dim, num_nodes_per_elem)]

DOMAINS = {"IHI": (0, 1), "ILO": (0, 0),
           "JHI": (1, 1), "JLO": (1, 0),
           "KHI": (2, 1), "KLO": (2, 0)}

def elem_volume(num_dim, num_nodes_per_elem, coords, thickness=None):
    """Volume definitions for several element types"""
    shape = (num_dim, num_nodes_per_elem)
    if shape == (2,4) or shape == (2,8):
        x, y = coords[:, [0, 1]].T
        A2  = (x[0]*y[1] - x[1]*y[0]) + (x[1]*y[2] - x[2]*y[1])
        A2 += (x[2]*y[3] - x[3]*y[2]) + (x[3]*y[0] - x[0]*y[3])
        return A2 / 2. * thickness
    if shape == (2,3) or shape == (2,8):
        x, y = coords[:, [0, 1]].T
        area = .5 * (x[0] * (y[1] - y[2]) +
                     x[1] * (y[2] - y[0]) +
                     x[2] * (y[0] - y[1]))
        return area * thickness
    if shape == (3,4) or shape == (3,8):
        m = zeros((4,4))
        m[:, 0] = 1.
        m[:, 1] = coords[:, 0]
        m[:, 2] = coords[:, 2]
        m[:, 3] = coords[:, 2]
        return det(m) / 6.


def elem_center_coord(num_dim, num_nodes_per_elem):
    """Coordinate of center of isoparametric element"""
    cp = {(1,2): array([0], dtype=float64),
          # Triangles
          (2,3): array([1, 1], dtype=float64) / 3.,
          (2,6): array([1, 1], dtype=float64) / 3.,
          # Quads
          (2,4): array([0, 0], dtype=float64),
          (2,8): array([0, 0], dtype=float64),
          # Tets
          (3,4): array([1, 1, 1], dtype=float64) / 4.,
          (3,10): array([1, 1, 1], dtype=float64) / 4.,
          # Hexs
          (3,8): array([0, 0, 0], dtype=float64),
          (3,20): array([0, 0, 0], dtype=float64),}
    return cp[(num_dim, num_nodes_per_elem)]

def elem_corner_coord(num_dim, num_nodes_per_elem):
    """Coordinates of corner nodes of isoparametric element"""
    xp = {(1,2): array([[-1, 1]], dtype=float64),
          # Triangles
          (2,3): array([[0, 0], [1, 0], [0, 1]], dtype=float64),
          (2,6): array([[0, 0], [1, 0], [0, 1]], dtype=float64),
          # Quads
          (2,4): array([[-1, -1], [1, -1], [1, 1], [-1, 1],
                        [0, -1], [1, 0], [0, 1], [-1, 0]], dtype=float64),
          (2,8): array([[-1, -1], [1, -1], [1, 1], [-1, 1],
                        [0, -1], [1, 0], [0, 1], [-1, 0]], dtype=float64),
          # Tets
          (3,4): array([[0, 0, 0], [1, 0, 0],
                        [0, 1, 0], [0, 0, 1]], dtype=float64),
          (3,10): array([[0, 0, 0], [1, 0, 0],
                        [0, 1, 0], [0, 0, 1]], dtype=float64),
          # Hexs
          (3,8): array([[-1, -1, -1], [ 1, -1, -1],
                        [ 1,  1, -1], [-1,  1, -1],
                        [-1, -1,  1], [ 1, -1,  1],
                        [ 1,  1,  1], [-1,  1,  1]], dtype=float64),
          (3,20): array([[-1, -1, -1], [ 1, -1, -1],
                        [ 1,  1, -1], [-1,  1, -1],
                        [-1, -1,  1], [ 1, -1,  1],
                        [ 1,  1,  1], [-1,  1,  1]], dtype=float64),}
    return xp[(num_dim, num_nodes_per_elem)]

class ElemGeom:
    """Element geometry properties"""
    def __init__(self, num_coord=None, num_el_node=None):
        self.num_coord = num_coord
        self.num_el_node = num_el_node
        self.num_face_nodes = num_face_nodes(num_coord, num_el_node)

    def face(self, region):
        return face(self.num_coord, self.num_el_node, region)

    def face_nodes(self, face_num):
        """Lists of nodes on element faces

        The nodes are ordered so that the element face forms either a 1D line
        element or a 2D surface element for 2D or 3D problems

        """
        return face_nodes(self.num_coord, self.num_el_node, face_num)

def num_face_nodes(num_coord, num_el_node):
    """Number of nodes on each element face.

    Useful for computing the surface integrals associated with the element
    traction vector

    """
    n = {(2,3): 2, (2,4): 2,
         (2,6): 3, (2,8): 3,
         (3,4): 3, (3,10): 6, (3,8): 4, (3,20): 8}[(num_coord, num_el_node)]
    return n

def face(num_coord, num_el_node, region):
    R = region.upper()
    if num_coord == 2:
        if num_el_node in (4, 8):
            d = {"ILO": 3, "IHI": 1, "JLO": 0, "JHI": 2}

    elif num_coord == 3:
        if num_el_node in (8, 20):
            d = {"ILO": 3, "IHI": 1, "JLO": 0, "JHI": 2, "KLO": 4, "KHI": 5}

    return d[R]

def face_nodes(num_coord, num_el_node, face_num):
    i3 = [1,2,0]
    i4 = [1,2,3,0]

    nodes = zeros(num_face_nodes(num_coord, num_el_node), dtype=int32)
    if num_coord == 2:
        if num_el_node == 3:
            nodes[0] = face_num
            nodes[1] = i3[face_num]
        elif num_el_node == 6:
            nodes[0] = face_num
            nodes[1] = i3[face_num]
            nodes[2] = face_num + 3
        elif num_el_node == 4:
            nodes[0] = face_num
            nodes[1] = i4[face_num]
        elif num_el_node == 8:
            nodes[0] = face_num
            nodes[1] = i4[face_num]
            nodes[2] = face_num + 4

    elif num_coord == 3:
        if num_el_node == 4:
            if face_num == 0:
                nodes[:] = [0, 1, 2]
            elif face_num == 1:
                nodes[:] = [0, 3, 1]
            elif face_num == 2:
                nodes[:] = [1, 3, 2]
            elif face_num == 3:
                nodes[:] = [2, 3, 0]

        elif num_el_node == 10:
            if  face_num == 0:
                nodes[:] = [0, 1, 2, 4, 5, 6]
            elif face_num == 1:
                nodes[:] = [0, 3, 1, 7, 8, 4]
            elif face_num == 2:
                nodes[:] = [1, 3, 2, 8, 9, 5]
            elif face_num == 3:
                nodes[:] = [2, 3, 0, 9, 7, 6]

        elif num_el_node == 8:
            if face_num == 0:
                nodes[:] = [0, 1, 2, 3]
            elif face_num == 1:
                nodes[:] = [4, 7, 6, 5]
            elif face_num == 2:
                nodes[:] = [0, 4, 5, 1]
            elif face_num == 3:
                nodes[:] = [1, 2, 6, 5]
            elif face_num == 4:
                nodes[:] = [2, 6, 7, 3]
            elif face_num == 5:
                nodes[:] = [3, 7, 4, 0]

        elif num_el_node == 20:
            if face_num == 0:
                nodes[:] = [0, 1, 2, 3, 8, 9, 10, 11]
            elif face_num == 1:
                nodes[:] = [4, 7, 6, 5, 15, 14, 13, 12]
            elif face_num == 2:
                nodes[:] = [0, 4, 5, 1, 16, 12, 17, 8]
            elif face_num == 3:
                nodes[:] = [1, 5, 6, 2, 17, 13, 18, 9]
            elif face_num == 4:
                nodes[:] = [2, 6, 7, 3, 18, 14, 5, 10]
            elif face_num == 5:
                nodes[:] = [3, 7, 4, 0, 19, 15, 16, 11]

    return nodes
