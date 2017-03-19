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


#@tjf: new
def el_gauss_weights():
    """Gauss weights for 2 point Gauss quadrature

    Returns
    -------
    w : ndarray of real (2, )
        The Gauss weights

    """
    return np.ones(2)


#@tjf: new
def el_gauss_points():
    """Gauss coordinates for 2 point Gauss quadrature

    Returns
    -------
    xi : ndarray of real (2, )
        The Gauss coordinates

    """
    return np.array([-1., 1.]) / ROOT3


#@tjf: new
def el_mapping(xi, coords):
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


#@tjf: new
def el_mapping_inv(x, coords):
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


#@tjf: new
def el_b_matrix(xi, coords):
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
    dNdxi = el_shape_deriv(xi)
    jac = el_jacobian(xi, coords)
    # Convert shape function derivatives to derivatives
    # wrt global coords
    dNdx = dNdxi / jac
    return dNdx


def el_shape(xi):
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


def el_shape_deriv(xi):
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


def el_jacobian(xi, coords):
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
    dNdxi = el_shape_deriv(xi)
    jac = np.dot(dNdxi, coords)
    return jac


def el_force(coords, q, cf=None):
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
    gauss_points = el_gauss_points()
    gauss_weights = el_gauss_weights()
    for (n, xi) in enumerate(gauss_points):
        # Gauss point and weight
        weight = gauss_weights[n]

        # shape function, jacobian, and distribued load
        N = el_shape(xi)
        jac = el_jacobian(xi, coords)
        qx = q(el_mapping(xi, coords))
        f += qx * N * jac * weight

    if cf is not None:
        # concentrated forces given on element interior
        xi = el_mapping_inv(cf[0], coords)
        N = el_shape(xi)
        f += cf[2] * N

    return f


def el_stiff(coords, area, prop):
    """Element force for a 1D linear element

    Parameters
    ----------
    coords : ndarray of real
        Element nodal coordinates
    area : func
        Element area
    prop : real
        Element property

    Returns
    -------
    k : ndarray or real (2, 2)
        The element stiffness array

    """
    # integrate stiffness by looping over Gauss points and summing contributions
    k = np.zeros((2, 2))
    gauss_points = el_gauss_points()
    gauss_weights = el_gauss_weights()
    for (n, xi) in enumerate(gauss_points):
        weight = gauss_weights[n]
        jac = el_jacobian(xi, coords)
        B = el_b_matrix(xi, coords)
        km = area(el_mapping(xi, coords)) * prop
        k += km * jac * weight * np.outer(B, B)
    return k


def ezfem(coords, conn, area, prop, bcs, bf=0., cfs=[], xcfs=[], enforce=0):
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

    # check enforcement type
    if enforce not in (0, 1):
        error("{0}: unkown bc enforcement type".format(enforce))

    # find elements corresponding to each xcf
    cfx = {}
    for xcf in xcfs:
        elem_num = find_elem_1d(xcf[0], coords, conn)
        cfx[elem_num] = xcf

    glob_stiff = np.zeros((num_dof, num_dof))
    glob_force = np.zeros(num_dof)
    glob_disp = np.zeros(num_dof)

    # assemble global stiffness
    for (elem_num, elem_nodes) in enumerate(conn):
        num_points = len(elem_nodes)
        elem_coords = coords[elem_nodes]
        elem_stiff = el_stiff(elem_coords, area, prop)
        elem_force = el_force(elem_coords, bf, cf=cfx.get(elem_num))

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
