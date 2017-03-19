import sys
import numpy as np


#@tjf: new
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


#@tjf: new
def el_shape(xval, coords):
    """Linear 1D shape functions

    Parameters
    ----------
    xval : real
        Point inside element
    coords : ndarray of real
        Element end points

    Returns
    -------
    N : ndarray or real (2, )
        The element shape function array at x

    """
    xa, xb = coords
    N = np.zeros(2)
    N[0] = (xb - xval) / (xb - xa)
    N[1] = (xval - xa) / (xb - xa)
    return N


#@tjf: new
def el_shape_deriv(xval, coords):
    """Derivative of linear 1D shape functions

    Parameters
    ----------
    coords : ndarray of real
        Element end points
    xval : real
        Point inside element

    Returns
    -------
    dN : ndarray or real (2, )
        The element shape function derivative array at x

    """
    xa, xb = coords
    dN = np.zeros(2)
    dN[0] = -1. / (xb - xa)
    dN[1] =  1. / (xb - xa)
    return dN


#@tjf: new
def el_force(coords, q):
    """Element force for a 1D linear element

    Parameters
    ----------
    coords : ndarray of real
        Element end points
    xval : real
        Point inside element
    q : func
        Element body force

    Returns
    -------
    f : ndarray or real (2, )
        The element force array

    """
    xa, xb = coords
    f = np.zeros(2)
    for i in range(2):
        f[i] = np.trapz([el_shape(x, coords)[i] * q(x) for x in coords], coords)
    return f


#@tjf: new
def el_stiff(coords, area, prop):
    """Element force for a 1D linear element

    Parameters
    ----------
    coords : ndarray of real
        Element end points
    area : func
        Element area
    prop : real
        Element property

    Returns
    -------
    k : ndarray or real (2, 2)
        The element stiffness array

    """
    xa, xb = coords
    k = np.zeros((2, 2))
    dN = el_shape_deriv
    for i in range(2):
        for j in range(2):
            y = [area(x) * prop * dN(x, coords)[i] * dN(x, coords)[j]
                 for x in coords]
            k[i, j] = np.trapz(y, coords)
    return k


def ezfem(coords, conn, area, prop, bcs, bf=0., cfs=[]):
    """Solve for displacements in a tapered bar using the FEM.

    Parameters
    ----------
    coords : ndarray of real (num_node,)
        The nodal coordinates
        coords[i] is the coordinate of the ith node
    conn : ndarray of int (num_elem, 2)
        The element connectivity
        conn[i, j] is the jth node of the ith element
    area : func
        Area of bar
    prop : real
        Material property
    bcs : list (2, 2)
        The boundary conditions
        bcs[i][0] is the boundary type of boundary
        bcs[i][1] the dof to apply bc (not used, yet)
        bcs[i][2] is the boundary magnitude
    bf : func, real, or ndarray of func or real
        Body force acting on bar.
    cfs : list (num_cf, 2)
        The concentrated forces
        cfs[i][0] is the node number of the ith concentrated force
        cfs[i][1] the dof to apply cf
        cfs[i][2] is the cf magnitude

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

    # check area
    if not isfunc(area):
        area = lambda x, a=area: a

    # check body force
    if not isfunc(bf):
        bf = lambda x, r=bf: r

    # check that concentrated forces are not applied on boundaries
    for (n, dof, mag) in cfs:
        if n in bndry:
            error("concentrated forces cannot be applied to boundary")

    glob_stiff = np.zeros((num_dof, num_dof))
    glob_force = np.zeros(num_dof)
    glob_disp = np.zeros(num_dof)

    # assemble global stiffness
    for (elem_num, elem_nodes) in enumerate(conn):
        num_points = len(elem_nodes)
        elem_coords = coords[elem_nodes]
        elem_stiff = el_stiff(elem_coords, area, prop)
        elem_force = el_force(elem_coords, bf)

        # add contributions to global matrices
        for a in range(num_points):
            I = elem_nodes[a]
            glob_force[I] += elem_force[a]
            for b in range(num_points):
                J = elem_nodes[b]
                glob_stiff[I, J] += elem_stiff[a, b]

    # Apply concentrated forces
    for (n, dof, mag) in cfs:
        glob_force[n] += mag

    # Apply boundary conditions
    for (i, bc) in enumerate(bcs):
        n = bndry[i]
        bct, dof, mag = bc
        if bct == 0:
            glob_stiff[n, :] = 0.
            glob_stiff[n, n] = 1.
            glob_force[n] = 0.
        glob_force[n] += mag

    glob_disp[:] = np.linalg.solve(glob_stiff, glob_force)

    return glob_disp
