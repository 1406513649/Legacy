import numpy as np

def gen_mesh_grid(shape, lengths, center=None):
    """Generate a 2D or 3D block mesh

    Parameters
    ----------
    shape : array of 2 or 3 ints
        Shape (counts of nodes in x, y, z)
    lengths : array of 2 or 3 floats
        Lengths of block
    center : array of 2 or 3 floats
        Center of block [0., 0., 0.]

    """
    lengths = np.asarray(lengths, dtype=np.float64)
    shape = np.asarray(shape, dtype=np.int32)
    if center is None:
        center = [0.] * len(lengths)
    center = np.asarray(center, dtype=np.float64)

    num_dim = shape.shape[0]
    assert num_dim in (1, 2, 3)

    # Generate nodal coordinates
    num_node = np.prod(shape)
    x0 = center - .5 * lengths
    assert np.all(shape - 1 > 0)
    dd = lengths / (shape - 1)

    ngrid = np.mgrid[[slice(ii) for ii in shape]]
    ngrid.shape = (num_dim, num_node)

    coords = x0 + ngrid.T * dd

    # generate the connectivity
    num_elem = np.prod(shape - 1)
    grid = np.arange(num_node, dtype=np.int32)
    grid.shape = shape

    if num_dim == 1:
        conn = np.zeros((num_elem, 2), dtype=np.int32)
        conn[:, 0] = grid[:-1]
        conn[:, 1] = grid[1:]

    elif num_dim == 2:
        conn = np.zeros((num_elem, 4), dtype=np.int32)
        conn[:, 0] = grid[:-1, :-1].flat
        conn[:, 1] = grid[1:, :-1].flat
        conn[:, 2] = grid[1:, 1:].flat
        conn[:, 3] = grid[:-1, 1:].flat

    elif num_dim == 3:
        conn = np.zeros((num_elem, 8), dtype=np.int32)
        conn[:, 0] = grid[:-1, :-1, :-1].flat
        conn[:, 1] = grid[1:, :-1, :-1].flat
        conn[:, 2] = grid[1:, 1:, :-1].flat
        conn[:, 3] = grid[:-1, 1:, :-1].flat
        conn[:, 4] = grid[:-1, :-1, 1:].flat
        conn[:, 5] = grid[1:, :-1, 1:].flat
        conn[:, 6] = grid[1:, 1:, 1:].flat
        conn[:, 7] = grid[:-1, 1:, 1:].flat

    node_num_map = dict([(i+1, i) for i in range(coords.shape[0])])
    elem_num_map = dict([(i+1, i) for i in range(conn.shape[0])])

    return coords, conn, node_num_map, elem_num_map


def gen_mesh_grid_2D_simple(shape, lengths):
    shape = np.asarray(shape)

    nx, ny = shape
    lx, ly = lengths

    xpoints = np.linspace(0, lx, nx)
    ypoints = np.linspace(0, ly, ny)

    coords = np.array([(x, y) for y in ypoints for x in xpoints])

    num_node = np.prod(shape)
    num_elem = np.prod(shape - 1)

    # Connectivity
    row = 0
    conn = np.zeros((num_elem, 4), dtype=np.int)
    nelx = xpoints.size - 1
    for elem_num in range(num_elem):
        ii = elem_num + row
        elem_nodes = [ii, ii + 1, ii + nelx + 2, ii + nelx + 1]
        conn[elem_num, :] = elem_nodes
        if (elem_num + 1) % (nelx) == 0:
            row += 1
        continue

    node_num_map = dict([(i+1, i) for i in range(coords.shape[0])])
    elem_num_map = dict([(i+1, i) for i in range(conn.shape[0])])
    return coords, conn, node_num_map, elem_num_map


def members_at_position(nodes, conn, axis, pos, tol=1E-08):
    """Returns nodes (and connected elements) whose position on the axis
    fall on pos.

    Parameters
    ----------
    axis : int
        Coordinate axis {x: 0, y: 1, z: 2}

    pos : float
        position

    """
    # find the nodes.
    # where returns a tuple of arrays, one for each
    # dimension of coords, containing the indices where the condition is
    # true of the elements in that dimension. Since we are only interested
    # in the node number - which corresponds to its row - we only take the
    # first component
    nodes = np.where(np.abs(nodes[:, axis] - pos) < tol)[0]
    elements = [i for node in nodes for (i, el) in enumerate(conn)
                if node >= 0 and node in el]
    return nodes, np.unique(elements)


def bounding_box(coords):
    """Return the box bounding the mesh

    Parameters
    ----------
    coords : array_like (num_node, num_dim)
        Array of nodal coordinates
        nodes[i, j] is the jth coord of the ith node

    Returns
    -------
    bounding_box : array_like (num_dim, 2)

    """
    num_node, num_dim = coords.shape
    bounding_box = np.empty((num_dim, 2))

    # xlims
    bounding_box[0] = [np.amin(coords[:, 0]), np.amax(coords[:, 0])]

    if num_dim > 1:
        # ylims
        bounding_box[1] = [np.amin(coords[:, 1]), np.amax(coords[:, 1])]

    if num_dim > 2:
        # zlims
        bounding_box[2] = [np.amin(coords[:, 2]), np.amax(coords[:, 2])]

    return bounding_box
