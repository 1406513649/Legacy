import sys
import numpy as np
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


def tapered_bar(coords, conn, ha, hb, thick, youngs_mod, end_force, bf=0.):
    """Solve for displacements in a tapered bar using the FEM.

    Parameters
    ----------
    coords : ndarray of real (num_node,)
        The nodal coordinates
        coords[i] is the coordinate of the ith node
    conn : ndarray of int (num_elem, 2)
        The element connectivity
        conn[i, j] is the jth node of the ith element
    ha, hb, thick : real
        Heights of the bar at :math:`x=x_a` and :math:`x=x_b`, and its
        thickness, respectively
    youngs_mod : real
        Young's modulus
    end_force : real
        Force acting on end of bar
    bf : real
        Force acting on body of bar

    Returns
    -------
    disp : ndarray of real (num_node,)
        The nodal displacements

    """
    na, nb = boundary_points_1d(coords)
    xa, xb = coords[[na, nb]]
    a_xa, a_xb = ha * thick, hb * thick
    area = lambda x: a_xa + x / (xb - xa) * (a_xb - a_xa)
    num_dof_per_node = 1
    num_node = coords.shape[0]
    num_elem = conn.shape[0]
    num_dof = num_node * num_dof_per_node

    glob_stiff = np.zeros((num_dof, num_dof))
    glob_force = np.zeros(num_dof)
    glob_disp = np.zeros(num_dof)

    # assemble global stiffness
    km = np.array([[1, -1], [-1, 1]], dtype=np.float64)
    fm = np.ones(2, dtype=np.float64)
    for (elem_num, elem_nodes) in enumerate(conn):
        num_points = len(elem_nodes)
        elem_coords = coords[elem_nodes]
        elem_length = coords[1] - coords[0]
        elem_area = area(elem_coords[0] + elem_length / 2.)
        elem_stiff = elem_area * youngs_mod / elem_length * km
        elem_force = bf * elem_length / 2. * fm

        # add contributions to global matrices
        for a in range(num_points):
            I = elem_nodes[a]
            glob_force[I] += elem_force[a]
            for b in range(num_points):
                J = elem_nodes[b]
                glob_stiff[I, J] += elem_stiff[a, b]

    # Apply boundary conditions
    glob_stiff[na, :] = 0.
    glob_stiff[na, na] = 1.
    glob_force[nb] = end_force
    glob_disp[:] = np.linalg.solve(glob_stiff, glob_force)

    return glob_disp
