import numpy as np
def uniform_bar(num_elem, xa, xb, area, youngs_mod, end_force, body_force=0.):
    """Solve for displacements in a uniform bar using the FEM.

    Parameters
    ----------
    num_elem : int
        The number of elements along the bar
    xa, xb : real
        `x` coordinates at left and right ends of bar, respectively
    area
        Area of bar
    youngs_mod : real
        Young's modulus
    end_force : real
        Force acting on end of bar

    Returns
    -------
    disp : ndarray of real (num_node,)
        The nodal displacements

    """
    num_dof_per_node = 1
    num_node = num_elem + 1
    coords = np.linspace(xa, xb, num_node)
    conn = np.array([[el, el+1] for el in range(num_elem)])

    num_dof = num_node * num_dof_per_node
    glob_stiff = np.zeros((num_dof, num_dof))
    glob_force = np.zeros(num_dof)
    glob_disp = np.zeros(num_dof)

    # loop over elements in the connectivity annd assemble global stiffness,
    # force
    km = np.array([[1, -1], [-1, 1]], dtype=np.float64)
    fm = np.ones(2, dtype=np.float64)
    for (elem_num, elem_nodes) in enumerate(conn):
        num_points = len(elem_nodes)
        elem_coords = coords[elem_nodes]
        elem_length = coords[1] - coords[0]
        elem_stiff = area * youngs_mod / elem_length * km
        elem_force = body_force * elem_length / 2. * fm

        # add contributions to global matrices
        for a in range(num_points):
            I = elem_nodes[a]
            glob_force[I] += elem_force[a]
            for b in range(num_points):
                J = elem_nodes[b]
                glob_stiff[I, J] += elem_stiff[a, b]

    # Apply boundary conditions
    glob_stiff[0, :] = 0.
    glob_stiff[0, 0] = 1.
    glob_force[-1] = end_force
    glob_disp[:] = np.linalg.solve(glob_stiff, glob_force)

    return glob_disp
