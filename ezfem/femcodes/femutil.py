import sys
import math
import numpy as np

# ----------------------------------------------------- Helper Functions ---- #
EPS = 1.E-12
TOL = 1.E-4
ROOT3 = math.sqrt(3.)
ROOT5 = math.sqrt(5.)


def isscalar(a):
    """Is a a scalar, or not?"""
    if isfunc(a):
        return False
    if isnum(a):
        return True
    return False


def isiterable(a):
    """Is a iterable?"""
    try: return bool([x for x in a])
    except TypeError: return False


def isnum(a):
    """Is a a number?"""
    try: return float(a)
    except (ValueError, TypeError): return False


def isfunc(f):
    """Is f a function, or not?"""
    try:
        f(1)
        return True
    except TypeError:
        return False


def error(message=None, xit=1):
    """Write a error message to stderr and quit"""
    sys.stderr.write("***error: {0}\n".format(message))
    if xit:
        sys.exit(xit)


def warn(message):
    """Write a warning message to stderr"""
    sys.stderr.write("***warning: {0}\n".format(message))


def zero_func(*args):
    """A zero function"""
    return 0.


def linmesh_1d(xa, xb, num_el, offset=0., start=0):
    """Create coordinates and connectivity for a linear 1d mesh"""
    coords = np.linspace(xa, xb, num_el + 1) + offset
    conn = np.array([[el, el+1] for el in range(num_el)], dtype=np.int32) + start
    return coords, conn


def quadmesh_1d(xa, xb, num_el, offset=0., start=0):
    """Create coordinates and connectivity for a quadratic 1d mesh"""
    coords = np.linspace(xa, xb, 2 * num_el + 1) + offset
    conn = np.array([[2*el, 2*el+2, 2*el+1]
                     for el in range(num_el)], dtype=np.int32) + start
    return coords, conn


def genmesh_1d(*args, **kwargs):
    """Generate a general 1D mesh.

    Parameters
    ----------
    args : tuple
        The args[i] are 3 tuples containing for each block of the mesh:
            num_el_in_blk, len_blk, el_type
    kwargs : dict
        Recognized keywords:
        offset : float
            Coordinate offset.  Applied by adding offset to each coordinate value

    """
    # recognized keywords
    offset = float(kwargs.get("offset", 0))

    # check input conforms
    spec = []
    errors = 0
    for (i, a) in enumerate(args):
        try:
            num_el_in_blk, len_blk, el_type = a
        except ValueError:
            errors += 1
            error("genmesh_1d: expected all args "
                  "to have len=3, got {0} in args[{1}]".format(a, i), xit=0)
            continue

        if abs(len_blk) < EPS:
            errors += 1
            error("genmesh_1d: expected all length arguments to be > 0, "
                  "got {0} in args[{1}]".format(len_blk, i), xit=0)
            continue

        num_el_in_blk = int(num_el_in_blk)
        if num_el_in_blk < 1:
            errors += 1
            error("genmesh_1d: expected all num_el_in_blk arguments to be >= 1, "
                  "got {0} in args[{1}]".format(num_el_in_blk, i), xit=0)
            continue

        el_type = el_type.lower()
        if el_type == "link2":
            el_type = "linear"
        elif el_type == "link3":
            el_type = "quadratic"

        if not re.search(r"(?i)qua|lin", el_type):
            errors += 1
            error("genmesh_1d: expected all el_type arguments to be one of "
                  "[quad, linear], got {0} in args[{1}]".format(el_type, i), xit=0)
            continue

        spec.append((len_blk, num_el_in_blk, el_type[0]))

    if errors:
        error("stopping due to previous errors")

    # generate the mesh
    elem_blks = []
    coords, conn = [], []
    len_dom = 0.
    num_node = 0
    num_elem = 0
    for i, (len_blk, num_el_in_blk, el_type) in enumerate(spec):
        xa = len_dom
        xb = xa + len_blk
        if el_type == "q":
            mesh = quadmesh_1d(xa, xb, num_el_in_blk)
        else:
            mesh = linmesh_1d(xa, xb, num_el_in_blk)

        # remove common coordinate from right/left ends of previous/current block
        coords.extend(mesh[0][(0 if not i else 1):])
        len_dom += len_blk

        # modify connectivity to account for previous nodes
        conn.extend(mesh[1] + num_node)

        elems_in_blk = range(num_elem, num_elem + num_el_in_blk)
        elem_blks.append(elems_in_blk)

        num_node += len(mesh[0]) - 1
        num_elem += num_el_in_blk

    coords = np.array(coords, dtype=np.float64) + offset

    # fix up the connectivity, putting -1 in empty node locations that arise,
    # for instance, for a mesh containing both 3 node quadratic elements and 2
    # node linear
    max_num_node = max(len(a) for a in conn)
    for (i, a) in enumerate(conn):
        conn[i] = [a[j] if j < len(a) else -1 for j in range(max_num_node)]
    conn = np.array(conn, dtype=np.int32)

    return coords, conn, elem_blks


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


def bounding_points_1d(point, points):
    """Find the indices of points that bound point

    Parameters
    ----------
    point : real
        The coordinate of the point to be bounded
    points : ndarray (num_pnt,)
        Coordinates of points

    Returns
    -------
    bounds : ndarray of int (2,)
        bounds[0] is the index of the point below
        bounds[1] is the index of the point above

    """
    points = np.asarray([_ for _ in enumerate(points)])
    equal = sorted(points[np.where(np.abs(points[:, 1] - point) < EPS)])
    if equal:
        return (equal[0][0],)
    below = sorted(points[np.where(point >= points[:, 1])], key=lambda x: x[1])
    above = sorted(points[np.where(point <= points[:, 1])], key=lambda x: x[1])
    if not below or not above:
        # outside of domain
        return
    return (int(below[-1][0]), int(above[0][0]))


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

    Raises
    ------
    ValueError if point lies outside of coords

    """
    if point > np.amax(coords) or point < np.amin(coords):
        errmsg = "coordinate point {0:.2f} lies outside coords".format(point)
        raise ValueError(errmsg)
    points = np.asarray([_ for _ in enumerate(coords)])
    conn = np.asarray(conn, dtype=np.int32)
    below = sorted(points[np.where(point >= points[:, 1])], key=lambda x: x[1])
    node_a = int(below[-1][0])
    return np.where(conn[:, 0] == node_a)[0][0]


if __name__ == "__main__":
    coords = np.linspace(0, 5, 10)
    conn = [[e, e+1] for e in range(len(coords))]
    print find_elem_at_point(1., coords, conn)
