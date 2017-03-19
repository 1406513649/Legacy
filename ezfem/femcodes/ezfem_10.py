import sys
import math
import numpy as np
from exolite import ExodusIIManager


HUGE = 1.E+60
ROOT3 = math.sqrt(3.)
ROOT5 = math.sqrt(5.)
TOL = 1.E-06


class EzFEM(object):

    def __init__(self, mesh, boundary, bf=0., cfs=[], xcfs=[], enforce=0):
        """Solve the FE equations associated with a 1D 2nd order BVP

        Parameters
        ----------
        mesh : instance
            A Mesh1D instance
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

        Notes
        -----
        bf can be a function applied over entire bar, real (constant)
        applied over entire bar, or an ndarray of containing body force for each
        element. In this case, len(bf) must = len(conn).

        """
        self.mesh = mesh
        self.num_dof_per_node = 1
        self.num_dof = self.mesh.num_node * self.num_dof_per_node
        self.disp = np.zeros(self.num_dof)

        # check body force
        if not isfunc(bf):
            bf = lambda x, r=bf: r
        self.bf = bf

        # boundary conditions
        self.boundary = boundary

        # check that concentrated forces are not applied on boundaries
        for (n, dof, mag) in cfs:
            if n in self.mesh.bndry:
                error("concentrated forces cannot be applied to boundary")
        self.cfs = cfs

        # check enforcement type
        if enforce not in (0, 1):
            error("{0}: unkown bc enforcement type".format(enforce))
        self.enforce = enforce

        # find elements corresponding to each xcf
        self.cfx = {}
        for xcf in xcfs:
            elem_num = self.mesh.find_elem(xcf[0])
            self.cfx[elem_num] = xcf

        # parse the element blocks and set up list of elements
        self.elements = np.empty(self.mesh.num_elem, dtype=np.dtype(object))
        for elem_blk in self.mesh.elem_blks:
            elem_blk_id, elems_in_blk, elem_type, elem_area, elem_mat = elem_blk

            # loop through each element and instantiate it
            for elem_num in elems_in_blk:
                elem_nodes = self.mesh.conn[elem_num][:elem_type.num_points]
                el = elem_type(elem_num, elem_nodes, elem_area, elem_mat)
                self.elements[elem_num] = el

        # The exodus database manager
        runid = "model"
        self.exo = ExodusIIManager(runid, self.mesh.coords,
                                   self.mesh.conn, self.mesh.elem_blks)

    def snapshot(self, u):
        self.exo.snapshot(u)

    def solve(self, solver="direct"):
        if solver[:3].lower() == "dir":
            self.direct_solve()
        elif solver[:3].lower() == "ite":
            self.iterative_solve()
        else:
            error("{0}: unkown solver".format(solver))

    def direct_solve(self):
        """Solve the FE equations

        """
        glob_stiff = np.zeros((self.num_dof, self.num_dof))
        glob_force = np.zeros(self.num_dof)
        glob_disp = np.zeros(self.num_dof)
        # get assembled matrices
        self.assemble_matrices(glob_disp, glob_stiff, glob_force)

        # Apply concentrated forces and boundary conditions
        self.apply_cfs(glob_force)
        self.apply_bcs(glob_stiff, glob_force)
        self.disp[:] = np.linalg.solve(glob_stiff, glob_force)
        self.snapshot(self.disp)
        return

    def iterative_solve(self):
        """Solve for the dependent variable using an iterative Newton method

        """
        u = np.zeros(self.mesh.num_node)
        du = np.zeros(self.mesh.num_node)
        for nit in range(25):

            # initialize global stiffness, force, displacement
            glob_stiff = np.zeros((self.mesh.num_node, self.mesh.num_node))
            glob_force = np.zeros(self.mesh.num_node)
            glob_resid = np.zeros(self.mesh.num_node)
            self.assemble_matrices(u, glob_stiff, glob_force, glob_resid)

            # Apply concentrated forces and boundary conditions
            self.apply_cfs(glob_force)
            # boundary conditions applied to the RHS
            rhs = glob_force - glob_resid
            self.apply_bcs(glob_stiff, rhs, u=u)

            # Now solve
            du[:] = np.linalg.solve(glob_stiff, rhs)
            u += du
            err1 = np.sqrt(np.dot(du, du))
            if err1 < TOL:
                break

        else:
            error("newton iterations failed to converge")

        self.disp[:] = u
        self.snapshot(self.disp)
        return

    def assemble_matrices(self, u, K, F, R=None):
        """Assemble the stiffness, force, and (optionally) the residual

        Notes
        -----
        To be more efficient with memory, K, F, and R are modified in place

        """
        for elem in self.elements:

            # element nodes, coordinates, and displacement
            elem_coords = self.mesh.coords[elem.nodes]
            elem_disp = u[elem.nodes]

            # element stiffness and force
            elem_stiff = elem.stiff(elem_coords, elem_disp)
            elem_force = elem.force(elem_coords, self.bf, cf=self.cfx.get(elem.num))
            if R is not None:
                elem_resid = elem.residual(elem_coords, elem_disp)

            # Add element contribution to global force and stiffness
            for a in range(elem.num_points):
                I = elem.nodes[a]
                F[I] += elem_force[a]
                if R is not None:
                    R[I] += elem_resid[a]
                for b in range(elem.num_points):
                    J = elem.nodes[b]
                    K[I, J] += elem_stiff[a, b]

    def apply_cfs(self, F):
        """Apply concentrated forces

        Parameters
        ----------
        F : ndarray of real (num_node*num_dof_per_node,)
            The external force array

        Notes
        -----
        To be more efficient with memory, F is modified in place

        """
        for (n, dof, mag) in self.cfs:
            F[n] += mag

    def apply_bcs(self, K, rhs, u=None):
        """Apply boundary conditions to model problem

                           Ku = F - Q                                  (1)
        Parameters
        ----------
        K : ndarray of real (num_node*num_dof_per_node, num_node*num_dof_per_node)
            The global stiffness
        rhs : ndarray of real (num_node*num_dof_per_node,)
            The right hand side of
        u : ndarray of real (num_node*num_dof_per_node,), optional, [None]
            current displacemet

        Notes
        -----
        To be more efficient with memory, K and rhs are modified in place

        u is supplied by iterative solvers to scale essential boundary
        conditions as the actual displacement approaches that required by the
        BC

        """
        # Apply boundary conditions
        for (i, bc) in self.boundary.items():
            n = self.mesh.bndry[i]
            bct, dof, mag = bc

            if u is not None and bct == 0:
                mag = mag - u[n]

            if self.enforce == 0:
                # direct substitution
                if bct == 0:
                    K[n, :] = 0.
                    K[n, n] = 1.
                    rhs[n] = 0.
                    rhs[n] += mag
            elif self.enforce == 1:
                # penalty method
                if bct == 0:
                    K[n, n] = HUGE
                    rhs[n] = HUGE * mag
                else:
                    rhs[n] += mag
            else:
                error("{0}: unkown bc enforcement type".format(enforce))
        return


class Element(object):
    order = None
    name = None
    num_points = None
    num_dof = None
    num_gauss = None
    gauss_weights = None
    gauss_points = None

    def stiff(self, coords, u):
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
        num_dof = self.num_points * self.num_dof
        k = np.zeros((num_dof, num_dof))
        for (n, xi) in enumerate(self.gauss_points):
            weight = self.gauss_weights[n]
            jac = self.jacobian(xi, coords)
            B = self.b_matrix(xi, coords)
            stran = np.dot(B, u)
            km = self.mat.get_stiff(stran)
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
        num_dof = self.num_points * self.num_dof
        f = np.zeros(num_dof)
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

    def residual(self, coords, u):
        """Compute the element residual using Gauss quadrature

        """
        # integrate element residual by looping over Gauss points and summing
        # contributions
        num_dof = self.num_points * self.num_dof
        r = np.zeros(num_dof)
        for (n, xi) in enumerate(self.gauss_points):
            # Gauss point and weight
            weight = self.gauss_weights[n]
            jac = self.jacobian(xi, coords)
            B = self.b_matrix(xi, coords)
            stran = np.dot(B, u)
            s = self.mat.get_stress(stran)
            r += s * B * jac * weight
        return r

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

    def iso_p_map(self, xi, coords):
        return np.dot(self.shape(xi), coords)

class LinearElement(Element):
    order = 1
    name = "Link2"
    num_points = 2
    num_dof = 1
    num_gauss = 2
    gauss_weights = np.ones(2)
    gauss_points = np.array([-1., 1.]) / ROOT3
    perturbation_only = False

    def __init__(self, num, nodes, area, mat):
        self.num = num
        self.nodes = nodes

        # check area
        if not isfunc(area):
            area = lambda x, a=area: a

        self.area = area
        self.mat = mat

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
        return self.iso_p_map(xi, coords)

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

class QuadraticElement(Element):
    order = 2
    name = "Link3"
    num_dim = 1
    num_dof = 1
    num_gauss = 3
    num_points = 3
    gauss_weights = np.array([5, 8, 5], dtype=np.float64) / 9.
    gauss_points = np.array([-1, 0, 1], dtype=np.float64) * ROOT3 / ROOT5
    def __init__(self, num, nodes, area, mat):
        self.num = num
        self.nodes = nodes

        # check area
        if not isfunc(area):
            area = lambda x, a=area: a

        self.area = area
        self.mat = mat

    def mapping(self, xi, coords):
        return self.iso_p_map(xi, coords)

    def mapping_inv(self, x, coords):
        a, b, c = coords
        d = (a ** 2 + 2. * a * b + 8. * a * c - 4. * a + b ** 2 -
             8. * b * c - 4. * b + 16. * c ** 2. + 4.)
        top = a + b - 2. + np.sqrt(d)
        bot = 2. * (a - b + 2 * c)
        return top / bot

    def shape(self, xi):
        """Evaluate the 1D element shape function

        """
        N = np.zeros(self.num_points)
        N[0] = -xi * (1 - xi)
        N[1] = xi * (1 + xi)
        N[2] = 2. * (1 - xi ** 2)
        return N / 2.

    def shape_deriv(self, xi):
        """Evaluate the derivative of the element shape function

        """
        dNdxi = np.zeros(self.num_points)
        dNdxi[0] = -1 + 2. * xi
        dNdxi[1] = 1 + 2 * xi
        dNdxi[2] = -4 * xi
        return dNdxi / 2.


class EulerBernouliBeamElement(Element):
    order = 2
    name = "Beam2"
    num_dim = 1
    num_dof = 2
    num_gauss = 3
    num_points = 2
    gauss_weights = np.array([5, 8, 5], dtype=np.float64) / 9.
    gauss_points = np.array([-1, 0, 1], dtype=np.float64) * ROOT3 / ROOT5
    perturbation_only = True
    def __init__(self, num, nodes, I, prop):
        self.num = num
        self.nodes = nodes

        # moment -> area (to work with other code)
        if not isfunc(I):
            I = lambda x, a=I: a
        self.E = prop
        self.area = I
        self.mat = BeamMaterial(self.E)

    def mapping(self, xi, coords):
        return self.iso_p_map(xi, coords)

    def shape(self, xi):
        """Evaluate the 1D element shape function

        """
        N = np.zeros(self.num_points)
        N[0] = -xi * (1 - xi)
        N[1] = xi * (1 + xi)
        N[2] = 2. * (1 - xi ** 2)
        return N / 2.

    def shape_deriv(self, xi):
        """Evaluate the derivative of the element shape function

        """
        dNdxi = np.zeros(self.num_points)
        dNdxi[0] = -1 + 2. * xi
        dNdxi[1] = 1 + 2 * xi
        dNdxi[2] = -4 * xi
        return dNdxi / 2.


class Material(object):
    name = None
    num_prop = None


class LinearElastic(Material):
    name = "elastic"
    num_prop = 1
    def __init__(self, props):
        self.E = props[0]

    @classmethod
    def check_props(self, props):
        """Check the material property array

        Parameters
        ----------
        props : ndarray
            props[0] is the Young's modulus, must be positive

        """
        E = props[0]
        if E < 0.:
            error("negative Young's modulus (E={0})".format(E))

    def get_stress(self, stran):
        """Compute the stress at stran

        Parameters
        ----------
        stran : real
            Strain

        Returns
        -------
        S : real
            Stress corresponding to stran

        """
        return self.E * stran

    def get_stiff(self, stran):
        """Compute the tangent stiffness

        Parameters
        ----------
        stran : real
            Strain

        Returns
        -------
        E : real
            Material tangent stiffness (Young's modulus)

        """
        return self.E

class NeoHookean(Material):
    name = "neo-hookean"
    num_prop = 1
    def __init__(self, props):
        self.E = props[0]

    @classmethod
    def check_props(self, props):
        """Check the material property array

        Parameters
        ----------
        props : ndarray
            props[0] is the Young's modulus, must be positive

        """
        E = props[0]
        if E < 0.:
            error("negative Young's modulus (E={0})".format(E))

    def get_stress(self, stran):
        """Compute the stress at stran

        Parameters
        ----------
        stran : real
            Strain

        Returns
        -------
        S : real
            Stress corresponding to stran

        """
        return self.E * stran * (stran + 2.) / 2. / (stran + 1.)

    def get_stiff(self, stran):
        """Compute the tangent stiffness

        Parameters
        ----------
        stran : real
            Strain

        Returns
        -------
        E : real
            Material tangent stiffness (Young's modulus)

        """
        stiff = self.E * (1. / 2. + 1. / 2. / ((stran + 1.) ** 2))
        return stiff

class BeamMaterial(Material):
    name = "beam"
    num_prop = 2
    def __init__(self, prop):
        self.E = prop[0]

    @classmethod
    def check_props(self, prop):
        """Check the material property array

        Parameters
        ----------
        props : ndarray
            props[0] is the Young's modulus, must be positive

        """
        E = prop[0]
        if E < 0.:
            error("negative Young's modulus (E={0})".format(E))

    def get_stiff(self, stran):
        """Beam element material stiffness -> linear elastic

        Parameters
        ----------
        stran : real
            Strain

        Returns
        -------
        E : real
            Material tangent stiffness (Young's modulus)

        """
        return self.E


def get_elem_by_name(elem_name):
    """Get the element type by element name

    Parameters
    ----------
    elem_name : str
        The element name

    Returns
    -------
    elem_type : object
        The uninstantiated element class

    """
    elements = (LinearElement, QuadraticElement)
    for elem in elements:
        if elem.name.lower() == elem_name.lower():
            return elem
    raise SystemExit("{0}: unknown element".format(elem_name))


def get_mat_by_name(mat_name):
    """Return the material class associated with mat_name

    Parameters
    ----------
    mat_name : str
        The material name

    Returns
    -------
    mat_class : object
        The uninstantiated material class

    """
    materials = (LinearElastic, NeoHookean)
    m = mat_name.lower()
    for material in materials:
        if material.name.lower()[:3] == m[:3]:
            return material
    error("material name {0} unrecognized".format(mat_name))


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


class _Mesh(object):
    pass

class Mesh1D(_Mesh):
    """The main mesh class

    """
    def __init__(self, *args, **kwargs):
        """Generate the mesh element blocks

        Parameters
        ----------
        args : tuple of lists
            args[i] is (length, number of elements, element name,
                        element area, material name, material properties)
            for the ith block.  The element name is sent to get_elem_by_name
            to determine the element type.
        kwargs : dict
            Optional keywords.
            offset : real
                Coordinates shall be offset by this much

        Example
        -------
        >>> elem_blk_1 = (4., 2, "Link2", a1, mat_name, prop)
        >>> elem_blk_2 = (3., 3, "Link2", a2, mat_name, prop)
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
                 elem_blk_area, elem_blk_mat, elem_blk_prop) = item
            except ValueError:
                raise SystemExit("expected 6 items per arg, "
                                 "got {0}".format(len(item)))

            # The element type
            elem_type = get_elem_by_name(elem_blk_elem)

            # get coords and connectivity for this block
            xb = xa + len_elem_blk

            item = (xa, xb, num_elem_in_blk)
            if elem_type.order == 1:
                elem_blk_coords, elem_blk_conn = self.gen_linmesh_1d(*item)
            elif elem_type.order == 2:
                elem_blk_coords, elem_blk_conn = self.gen_quadmesh_1d(*item)

            # add this blocks coords and connectivity to global coords and
            # connectivity
            coords = np.append(coords, elem_blk_coords[1:])
            conn.extend(elem_blk_conn + num_node)

            # set up this element block
            elems_in_blk = np.arange(len(elem_blk_conn)) + num_elem

            elem_mat = get_mat_by_name(elem_blk_mat)(elem_blk_prop)
            elem_blk = [i, elems_in_blk, elem_type, elem_blk_area, elem_mat]
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

        self.coords = coords + offset
        self.conn = conn
        self.elem_blks = elem_blks
        self.bndry = self.boundary_points_1d(self.coords)
        self.num_node = self.coords.shape[0]
        self.num_elem = self.conn.shape[0]

    def gen_linmesh_1d(self, xa, xb, num_elem):
        """Generate a 1D finite element mesh

        Parameters
        ----------
        xa, xb : real
            The left and right end points of the problem domain, respectively
        num_elem : int
           The number of elements

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
            error("gen_linmesh_1d: xa must be < xb")
        if num_elem < 1:
            error("gen_linmesh_1d: num_elem must be >= 1")
        coords = np.linspace(xa, xb, num_elem+1)
        conn = np.array([[i, i+1] for i in range(num_elem)])
        return coords, conn

    def gen_quadmesh_1d(self, xa, xb, num_elem):
        """Create coordinates and connectivity for a quadratic 1d mesh

        Parameters
        ----------
        xa, xb : real
            The left and right end points of the problem domain, respectively
        num_elem : int
           The number of elements

        Returns
        -------
        coords : ndarray of real (num_node,)
            The nodal coordinates
            coords[i] is the coordinate of the ith node
        conn : ndarray of int (num_elem, 2)
            The element connectivity
            conn[i, j] is the jth node of the ith element

        """
        coords = np.linspace(xa, xb, 2 * num_elem + 1)
        conn = np.array([[2*el, 2*el+2, 2*el+1]
                         for el in range(num_elem)], dtype=np.int32)
        return coords, conn

    def boundary_points_1d(self, coords):
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

    def find_elem(self, point):
        return self.find_elem_1d(point)

    def find_elem_1d(self, point):
        """Find the element at point

        Parameters
        ----------
        point : real
            The coordinate of the point

        Returns
        -------
        elem_id : int
            Integer ID of element

        """
        if point > np.amax(self.coords) or point < np.amin(self.coords):
            errmsg = "coordinate point {0:.2f} lies outside coords".format(point)
            error(errmsg)
        points = np.asarray([_ for _ in enumerate(self.coords)])
        below = sorted(points[np.where(point >= points[:, 1])], key=lambda x: x[1])
        node_a = int(below[-1][0])
        elem = np.where(self.conn[:, 0] == node_a)[0]
        if not elem and self.conn.shape[1] == 3:
            # interior node of quadratic element
            elem = np.where(self.conn[:, 2] == node_a)[0]
        return elem[0]


EBC = 0
NBC = 1
ILO = 0
IHI = 1
class Boundary1D(object):
    bc_types = {"essential": EBC, "natural": NBC}
    bc_locs = {"ilo": ILO, "ihi": IHI}
    def __init__(self):
        """The boundary condition class

        """
        self.bc_dict = {}
        self.ebc_defined = False

    def assign_bc(self, bc_type, bc_loc, bc_mag, bc_dof=0):
        """Assign a boundary condition

        """
        try:
            bc_type = self.bc_types[bc_type.lower()]
        except KeyError:
            error("bc type must be one of {0}".format(" ".join(self.bc_types)))
        try:
            bc_loc = self.bc_locs[bc_loc.lower()]
        except KeyError:
            error("bc location must be one of {0}".format(" ".join(self.bc_locs)))
        try:
            bc_mag = float(bc_mag)
        except ValueError:
            error("bc magnitude must be a real")
        try:
            bc_dof = int(bc_mag)
        except ValueError:
            error("bc dof must be a int")

        self.bc_dict[bc_loc] = (bc_type, bc_dof, bc_mag)
        if bc_type == EBC:
            # essential
            self.ebc_defined = True

    @property
    def constrained(self):
        return self.ebc_defined

    def items(self):
        return self.bc_dict.items()
