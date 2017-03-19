import sys
import math
import numpy as np


HUGE = 1.E+60
ROOT3 = math.sqrt(3.)


def isfunc(f):
    """Is f a function, or not?

    Parameters
    ----------
    f : object

    Returns
    -------
    is_f_a_func : bool
        True if f is a function, False otherwise

    """
    try:
        f(1)
        return True
    except TypeError:
        return False


def error(message):
    """Issue an error message and exit

    Parameters
    ----------
    message : str
        The error message

    Raises
    ------
    SystemExit
    """
    raise SystemExit("***error: {0}".format(message))


def linmesh_1d(xa, xb, num_elem, offset=0):
    """Generate a 1D finite element mesh

    Parameters
    ----------
    xa, xb : real
        The left and right end points of the problem domain, respectively
    num_elem : int
       The number of elements
    offset : real, optional [0.]
        Offset the nodal coordinates by this much.  e.g., the mesh
        domain would become [xa+offset, xb+offset]

    Returns
    -------
    coords : ndarray of real (num_node,)
        The nodal coordinates
        coords[i] is the coordinate of the ith node
    conn : ndarray of int (num_elem, 2)
        The element connectivity
        conn[i, j] is the jth node of the ith element
    """
    if xa > xb:
        error("linmesh_1d: xa must be < xb")
    if num_elem < 1:
        error("linmesh_1d: num_elem must be >= 1")
    coords = np.linspace(xa, xb, num_elem+1) + offset
    conn = np.array([[i, i+1] for i in range(num_elem)])
    return coords, conn


def boundary_points_1d(coords):
    """Check mesh and determine node IDs of boundary nodes

    Parameters
    ----------
    coords : ndarray or real (num_node, )
        Nodal coordinates
        coords[i] is the coordinate of the ith node

    Returns
    -------
    bound : ndarray of int (2,)
        Left end, right end node numbers

    """
    # determine the left and right boundary nodes
    l = sorted(enumerate(coords), key=lambda x: x[1])
    return [l[0][0], l[-1][0]]


def find_elem_1d(point, coords, conn):
    """Find the element at point

    Parameters
    ----------
    point : real
        The coordinate of the point
    coords : ndarray (num_node,)
        Nodal coordinates
    conn : ndarray of int (num_elem, num_pnt_per_elem)
        Element connectivity

    Returns
    -------
    elem_id : int
        Integer ID of element

    """
    if point > np.amax(coords) or point < np.amin(coords):
        errmsg = "coordinate point {0:.2f} lies outside coords".format(point)
        error(errmsg)
    points = np.asarray([_ for _ in enumerate(coords)])
    conn = np.asarray(conn, dtype=np.int32)
    below = sorted(points[np.where(point >= points[:, 1])], key=lambda x: x[1])
    node_a = int(below[-1][0])
    return np.where(conn[:, 0] == node_a)[0][0]


def ezfem(coords, conn, elem_blks, bcs, bf=0., cfs=[], xcfs=[], enforce=0):
    """Solve for displacements in a tapered bar using the FEM.

    Parameters
    ----------
    coords : ndarray of real (num_node,)
        The nodal coordinates
        coords[i] is the coordinate of the ith node
    conn : ndarray of int (num_elem, 2)
        The element connectivity
        conn[i, j] is the jth node of the ith element
    elem_blks : list of list
        element block information
        elem_blks[i] contains for the ith element block:
            elem_blk_id, elems_in_blk, elem_type, elem_blk_area, elem_blk_prop
    bcs : list (2, 2)
        The boundary conditions
        bcs[i][0] is the boundary type of boundary
        bcs[i][1] the dof to apply bc (not used, yet)
        bcs[i][2] is the boundary magnitude
    bf : func, real, or ndarray of func or real
        Body force acting on bar.
    cfs : list (num_cf, 3)
        The concentrated forces
        cfs[i][0] is the node number of the ith concentrated force
        cfs[i][1] the dof to apply cf
        cfs[i][2] is the cf magnitude
    xcfs : list (num_xcf, 3)
        The concentrated forces
        cfs[i][0] coordinate location of force
        cfs[i][1] the dof to apply cf
        cfs[i][2] is the cf magnitude
    enforce : int, optional [0]
        Boundary condition enforcement type
        0 -> direct substitution
        1 -> penalty method

    Returns
    -------
    disp : ndarray of real (num_node,)
        The nodal displacements

    Notes
    -----
    bf can be a function applied over entire bar, real (constant)
    applied over entire bar, or an ndarray of containing body force for each
    element. In this case, len(bf) must = len(conn).

    """
    bndry = boundary_points_1d(coords)
    num_dof_per_node = 1
    num_elem = conn.shape[0]
    num_node = coords.shape[0]
    num_dof = num_node * num_dof_per_node

    # check body force
    if not isfunc(bf):
        bf = lambda x, r=bf: r

    # check that concentrated forces are not applied on boundaries
    for (n, dof, mag) in cfs:
        if n in bndry:
            error("concentrated forces cannot be applied to boundary")

    # check enforcement type
    if enforce not in (0, 1):
        error("{0}: unkown bc enforcement type".format(enforce))

    # find elements corresponding to each xcf
    cfx = {}
    for xcf in xcfs:
        elem_num = find_elem_1d(xcf[0], coords, conn)
        cfx[elem_num] = xcf

    # parse the element blocks and set up list of elements
    elements = np.empty(num_elem, dtype=np.dtype(object))
    for elem_blk in elem_blks:
        elem_blk_id, elems_in_blk, elem_type, elem_area, elem_prop = elem_blk

        # loop through each element and instantiate it
        for elem_num in elems_in_blk:
            elem_nodes = conn[elem_num]
            el = elem_type(elem_num, elem_nodes, elem_area, elem_prop)
            elements[elem_num] = el

    glob_stiff = np.zeros((num_dof, num_dof))
    glob_force = np.zeros(num_dof)
    glob_disp = np.zeros(num_dof)

    # assemble global stiffness
    for elem in elements:
        elem_coords = coords[elem.nodes]
        elem_stiff = elem.stiff(elem_coords)
        elem_force = elem.force(elem_coords, bf, cf=cfx.get(elem.num))
        # add contributions to global matrices
        for a in range(elem.num_points):
            I = elem.nodes[a]
            glob_force[I] += elem_force[a]
            for b in range(elem.num_points):
                J = elem.nodes[b]
                glob_stiff[I, J] += elem_stiff[a, b]

    # Apply concentrated forces
    for (n, dof, mag) in cfs:
        glob_force[n] += mag

    # Apply boundary conditions
    for (i, bc) in enumerate(bcs):
        n = bndry[i]
        bct, dof, mag = bc
        if enforce == 0:
            # direct substitution
            if bct == 0:
                glob_stiff[n, :] = 0.
                glob_stiff[n, n] = 1.
                glob_force[n] = 0.
            glob_force[n] += mag
        elif enforce == 1:
            # penalty method
            if bct == 0:
                glob_stiff[n, n] = HUGE
                glob_force[n] = HUGE * mag
            else:
                glob_force[n] += mag
        else:
            error("{0}: unkown bc enforcement type".format(enforce))

    glob_disp[:] = np.linalg.solve(glob_stiff, glob_force)

    return glob_disp


class Element(object):
    order = None
    name = None
    num_points = None
    num_dof = None
    num_gauss = None
    gauss_weights = None
    gauss_points = None

    def stiff(self, coords):
        """Element force for a 1D linear element

        Parameters
        ----------
        coords : ndarray of real
            Element nodal coordinates

        Returns
        -------
        k : ndarray or real (2, 2)
            The element stiffness array

        """
        # integrate stiffness by looping over Gauss points and summing
        # contributions
        k = np.zeros((2, 2))
        for (n, xi) in enumerate(self.gauss_points):
            weight = self.gauss_weights[n]
            jac = self.jacobian(xi, coords)
            B = self.b_matrix(xi, coords)
            km = self.area(self.mapping(xi, coords)) * self.prop
            k += km * jac * weight * np.outer(B, B)
        return k

    def force(self, coords, q, cf=None):
        """Element force for a 1D linear element

        Parameters
        ----------
        coords : ndarray of real
            Element nodal coordinates
        xval : real
            Point inside element
        q : func
            Element body force
        cf : list, optional [None]
            Element concentrated force
            If given, it shall be of the form
            cf[0] - location of concentrated force
            cf[1] - concentrated force dof (not used)
            cf[2] - magnitude of concentrated force

        Returns
        -------
        f : ndarray or real (2, )
            The element force array

        """
        f = np.zeros(2)
        for (n, xi) in enumerate(self.gauss_points):
            # Gauss point and weight
            weight = self.gauss_weights[n]

            # shape function, jacobian, and distribued load
            N = self.shape(xi)
            jac = self.jacobian(xi, coords)
            qx = q(self.mapping(xi, coords))
            f += qx * N * jac * weight

        if cf is not None:
            # concentrated forces given on element interior
            xi = self.mapping_inv(cf[0], coords)
            N = self.shape(xi)
            f += cf[2] * N

        return f

    def jacobian(self, xi, coords):
        """Compute the Jacobian of the element deformation

        Parameters
        ----------
        xi : real
            Gauss point
        coords : ndarray
            Nodal coordinates, [left_node, right_node]

        Returns
        -------
        jac : real
            Jacobian of the deformation

        Notes
        -----
        The Jacobian is defined by

                  dN
            J =  --- . x
                 dxi

        """
        dNdxi = self.shape_deriv(xi)
        jac = np.dot(dNdxi, coords)
        return jac

    def b_matrix(self, xi, coords):
        """Element B matrix

        Parameters
        ----------
        xi : real
            location in the natural coordinates
        coords : ndarray of real
            Element nodal coordinates

        Returns
        -------
        B : ndarray of real
            Element B matrix dNdx

        """
        dNdxi = self.shape_deriv(xi)
        jac = self.jacobian(xi, coords)
        # Convert shape function derivatives to derivatives
        # wrt global coords
        dNdx = dNdxi / jac
        return dNdx


class LinearElement(Element):
    order = 1
    name = "Link2"
    num_points = 2
    num_dof = 1
    num_gauss = 2
    gauss_weights = np.ones(2)
    gauss_points = np.array([-1., 1.]) / ROOT3

    def __init__(self, num, nodes, area, prop):
        self.num = num
        self.nodes = nodes

        # check area
        if not isfunc(area):
            area = lambda x, a=area: a

        self.area = area
        self.prop = prop

    def mapping(self, xi, coords):
        """Mapping from natural to physical coordinates

        Parameters
        ----------
        xi : real
            Position in natural coordinate
        coords : ndarray of real
            Element nodal coordinates

        Returns
        -------
        x : real
            x in the physical coordinates

        """
        return coords[0] + (coords[1] - coords[0]) / 2. * (1 + xi)

    def mapping_inv(self, x, coords):
        """Mapping from physical to natural coordinates

        Parameters
        ----------
        x : real
            x in the physical coordinates
        coords : ndarray of real
            Element nodal coordinates

        Returns
        -------
        xi : real
            Position in natural coordinate

        """
        return (x - coords[0]) / (coords[1] - coords[0]) * 2. - 1

    def shape(self, xi):
        """Linear 1D shape functions

        Parameters
        ----------
        xi : real
            Point inside element in natural coordinates

        Returns
        -------
        N : ndarray of real (2, )
            The element shape function array at xi

        """
        N = np.zeros(2)
        N[0] = 1 - xi
        N[1] = 1 + xi
        return N / 2.

    def shape_deriv(self, xi):
        """Derivative of linear 1D shape functions

        Parameters
        ----------
        xi : real
            Point inside element in natural coordinates

        Returns
        -------
        dNdxi : ndarray or real (2, )
            The element shape function derivative array at xi

        """
        dNdxi = np.zeros(2)
        dNdxi[0] = -1.
        dNdxi[1] = 1.
        return dNdxi / 2.

def get_elem_by_name(elem_name):
    elements = (LinearElement, )
    for elem in elements:
        if elem.name.lower() == elem_name.lower():
            return elem
    raise SystemExit("{0}: unknown element".format(elem_name))


def gen_elem_blks(*args, **kwargs):
    """Generate element blocks

    Parameters
    ----------
    args : tuple of lists
        args[i] is (length, number of elements, element name,
                    element area, element properties)
        for the ith block.  The element name is sent to get_elem_by_name
        to determine the element type.
    kwargs : dict
        Optional keywords.
        offset : real
            Coordinates shall be offset by this much

    Returns
    -------
    elem_blks : list of lists
        elem_blks[i] is (element block number, elements in block,
                         element type, element area, element properties)

    Example
    -------
    >>> elem_blk_1 = (4., 2, "Link2", a1, prop)
    >>> elem_blk_2 = (3., 3, "Link2", a2, prop)
    >>> coords, conn, elem_blocks = gen_elem_blocks(elem_blk_1, elem_blk_2)

    """
    xa = 0.
    coords = np.array(xa)
    conn = []
    elem_blks = []
    num_elem = 0
    num_node = 0
    for (i, item) in enumerate(args):
        try:
            # l : length of element block
            (len_elem_blk, num_elem_in_blk, elem_blk_elem,
             elem_blk_area, elem_blk_prop) = item
        except ValueError:
            raise SystemExit("expected 5 items per arg, got {0}".format(len(item)))

        # get coords and connectivity for this block
        xb = xa + len_elem_blk
        elem_blk_coords, elem_blk_conn = linmesh_1d(xa, xb, num_elem_in_blk)

        # add this blocks coords and connectivity to global coords and
        # connectivity
        coords = np.append(coords, elem_blk_coords[1:])
        conn.extend(elem_blk_conn + num_node)

        # set up this element block
        elem_type = get_elem_by_name(elem_blk_elem)
        elems_in_blk = np.arange(len(elem_blk_conn)) + num_elem
        elem_blk = [i, elems_in_blk, elem_type, elem_blk_area, elem_blk_prop]
        elem_blks.append(elem_blk)

        xa = xb
        num_elem += len(elems_in_blk)
        num_node += len(elem_blk_coords) - 1

    # fix up the connectivity, putting -1 in empty node locations that arise,
    # for instance, for a mesh containing both 3 node quadratic elements and 2
    # node linear
    max_num_node = max(len(a) for a in conn)
    for (i, a) in enumerate(conn):
        conn[i] = [a[j] if j < len(a) else -1 for j in range(max_num_node)]
    conn = np.array(conn, dtype=np.int32)

    offset = kwargs.get("offset", 0.)

    return coords + offset, conn, elem_blks


if __name__ == "__main__":
    elem_blk_1 = (4., 2, "Link2", 2., 1.)
    elem_blk_2 = (3., 3, "Link2", 2., 1.)
    coords, conn, elem_blks = gen_elem_blks(elem_blk_1, elem_blk_2, offset=-4.)
