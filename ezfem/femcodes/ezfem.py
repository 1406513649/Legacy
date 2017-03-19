import os
import re
import sys
import numpy as np
from exolite import ExodusIIManager
np.set_printoptions(precision=2)

from femutil import *


# ---------------------------------------------------------------- Model ---- #
class FEModel(object):

    def __init__(self, coords, conn, elem_blks, o=1, solver=None):
        """Initialize the FE Model object

        Parameters
        ----------
        coords : ndarray
            Nodal coordinates.  coords[i, j] is the jth coordinate
            of the ith node
        conn : ndarray
            Nodal connectivity.  conn[i, j] is the jth node ID of the ith element
        elem_blks : list
            Element block information.  elem_blks[i] contains
              (elem_blk_id, elements, element type, material, material properties)
              for the ith element block
        o : int, optional [1]
            The array offset
        solver : str, optional [direct]
            The solver to use

        """
        # check solver
        if solver is None:
            solver = "direct"
        self.solver = solver.lower()

        if self.solver[:3] not in ("dir", "ite"):
            error("{0}: unknown solver".format(solver))

        # set up the geometry
        self.conn = np.array(conn, dtype=np.int32) - o
        self._coords = coords
        self.num_elem = self.conn.shape[0]
        self.num_node = self._coords.shape[0]

        # make sure elements define a positive length
        if np.any(np.diff(self._coords) < 0.):
            error("coords must be monitonically increasing over domain")

        self.boundary_nodes = boundary_points_1d(self._coords)

        # instantiate each element
        self.elements = np.empty(self.num_elem, dtype=np.dtype(object))
        for elem_blk in elem_blks:
            elem_blk_id, elems, elem_type, mat_type, mat_props = elem_blk

            # instantiate material
            elem_mat = mat_type(mat_props)

            # loop through each element and instantiate it
            for elem_num in elems:
                elem_nodes = self.conn[elem_num]
                el = elem_type(elem_num, elem_nodes, elem_mat)
                self.elements[elem_num] = el

        # place holder for displacement
        self._disp = np.empty(self.num_node)

        # setup the generalized boundary conditions array
        #                      node          alpha, beta, gamma
        self.bcs = [[self.boundary_nodes[0], None,  None, None],
                    [self.boundary_nodes[1], None,  None, None]]
        # set to True when model is properly constrained
        self.constrained = False

        # defaults for forces, distributed load
        self.cfs = []
        self.q_func = zero_func

        # The exodus database manager
        self.exo = ExodusIIManager()
        elem_num_map = range(self.num_elem)
        side_sets = []
        node_sets = []
        elem_blx = []
        elem_data = []
        elem_var_names = ["STRESS", "STRAIN"]
        exo_coords = np.column_stack((self._coords, np.zeros(self.num_node)))
        for elem_blk in elem_blks:
            ebid, elems, elem_type, mat_type, mat_props = elem_blk
            nnodes = len([n for n in self.conn[elems[0]] if n != -1])
            neeb = len(elems)
            elem_blx.append([ebid, elems, "TRUSS", nnodes, elem_var_names])
            elem_data.append([ebid, neeb, np.zeros((neeb, len(elem_var_names)))])
        self.exo.put_init("model", 2, exo_coords, self.conn, elem_blx,
                          node_sets, side_sets, elem_data, elem_num_map)
        self.elem_blks = elem_blks

        pass

    def dist_load(self, x):
        return self.q_func(x)

    @property
    def boundary_conditions(self):
        return self.bcs

    @property
    def conc_forces(self):
        return self.cfs

    @property
    def disp(self):
        return self._disp

    @property
    def coords(self):
        return self._coords

    def assign_distributed_load(self, q):
        """Assign a distributed load to the model

        Parameters
        ----------
        dist_load : real, or function
            The distributed load, to be applied to entire body

        """
        if not isfunc(q):
            # distributed load is not a function, convert it to one
            q = lambda x: q
        self.q_func = q

    def assign_bc(self, loc, type, magnitude):
        """Assign boundary condition to the model

        Parameters
        ----------
        loc : str
            The boundary location.  Must be one of ilo or ihi
        type : str
            The type of boundary condition to assign.  Must be one of
            (essential, dirichlet) or (natural, neumann)

        magnitude : real
            The dof magnitude

        """
        if loc.lower() not in ("ilo", "ihi"):
            error("assign_bc: loc must be one of ilo or ihi, got {0}".format(loc))

        # get boundary condition type
        tl = type.lower()
        if tl[:3] in ("ess", "dir"):
            alpha, beta, gamma = 1., 0., magnitude
        elif tl[:3] in ("nat", "neu"):
            alpha, beta, gamma = 0., 1., magnitude
        else:
            error("assign_bc: type must be one of essential or natural, "
                  "got {0}".format(loc))
        self.assign_generalized_bc(loc, alpha, beta, gamma)

    def assign_generalized_bc(self, loc, alpha, beta, gamma):
        """Assign a generalized boundary condition to the model

        Parameters
        ----------
        loc : str
            The boundary location.  Must be one of ilo or ihi
        alpha, beta, gamma : real
            The generalized boundary condition coefficients

        """
        if loc.lower() == "ilo":
            idx = 0
        elif loc.lower() == "ihi":
            idx = 1
        else:
            error("assign_bc: loc must be one of ilo or ihi, got {0}".format(loc))

        # determine if boundary already has an assigned bc
        if self.bcs[idx][1] is not None:
            error("attempting to assign multiple boundary conditions to same node")

        if abs(beta) < EPS:
            beta = 1.e-80

        # algorithm requires negative on left side boundary
        if idx == 0:
            beta = -beta

        if abs(alpha - 1.) < EPS:
            self.constrained = True

        self.bcs[idx] = [self.boundary_nodes[idx], alpha, beta, gamma]

    def assign_conc_force(self, point, magnitude, placement="node", o=1):
        """Assign a concentrated force to the model

        Parameters
        ----------
        point : int or real
            The node, or spatial location, to apply concentrated force
        magnitude : real
            The force magnitude
        placement : str, optional [node]
            Optional identifier of where to apply force.
            One of [node, point]

        """
        placement = placement.lower()
        if not re.search(r"(?i)point|coord|node|no|n", placement):
            error("{0}: bad placement of concentrated force".format(placement))
        if placement[0] != "n" and self.elements[0].order != 1:
            error("concentrated forces must be assigned to nodes for "
                  "higher order elements")

        if placement[0] == "n":
            if point == -1:
                point = self.num_node
            point -= o
            if point not in range(self.num_node):
                error("{0}: invalid node number".format(point))
            if point in self.boundary_nodes:
                loc = "ilo" if point == self.boundary_nodes[0] else "ihi"
                alpha, beta, gamma = 0., 1., magnitude
                self.assign_generalized_bc(loc, alpha, beta, gamma)
            else:
                self.cfs.append([point, magnitude])
            return

        # split concentrated load between adjacent nodes
        nodes = bounding_points_1d(point, self.coords)
        if nodes is None:
            error("{0}: outside of problem domain".format(point))

        if len(nodes) == 1:
            # concentrated force assigned to single node
            self.cfs.append([nodes[0], magnitude])
            return

        # find the element
        for elem in self.elements:
            if nodes[0] in elem.nodes and nodes[1] in elem.nodes:
                break
        else:
            error("Unable to find element at {0}".format(point))

        # split the magnitude between adjacent nodes
        elem_nodes = self.conn[elem.num][:elem.num_points]
        elem_coords = self.coords[elem_nodes]
        fac = (elem_coords[1] - point) / (elem_coords[1] - elem_coords[0])
        self.cfs.append([nodes[0], magnitude * fac])
        self.cfs.append([nodes[1], magnitude * (1. - fac)])
        return

    def check_bc(self):
        if not self.constrained:
            error("model not sufficiently constrained")

        for i, (n, alpha, beta, gamma) in enumerate(self.bcs):
            if alpha is None:
                # no bc explicityly given -> zero flux condition
                self.bcs[i][1:] = [0., 1., 0.]
                continue

    def solve(self):
        """Solve for the dependent variable

        """
        self.check_bc()

        if self.solver[:3] == "dir":
            self.direct_solve()
        elif self.solver[:3] == "ite":
            self.iterative_solve()
        else:
            error("{0}: unknown solver".format(self.solver))

    def direct_solve(self):
        """Solve for the dependent variable using a direct method

        """
        # initialize global stiffness, force, displacement
        glob_stiff = np.zeros((self.num_node, self.num_node))
        glob_force = np.zeros(self.num_node)
        disp = np.zeros(self.num_node)

        # Assemble the global stiffness and force
        for elem in self.elements:

            # element nodes, coordinates, and displacement
            elem_nodes = self.conn[elem.num][:elem.num_points]
            elem_coords = self.coords[elem_nodes]
            elem_disp = disp[elem_nodes]

            # element stiffness and force
            elem_stiff = elem.stiffness(elem_coords, elem_disp)
            elem_force = elem.force(self.dist_load, elem_coords)

            # Add element contribution to global force and stiffness
            for a in range(elem.num_points):
                I = elem_nodes[a]
                glob_force[I] += elem_force[a]
                for b in range(elem.num_points):
                    J = elem_nodes[b]
                    glob_stiff[I, J] += elem_stiff[a, b]

        # Concentrated forces
        for (node, mag) in self.conc_forces:
            glob_force[node] += mag

        # Apply boundary conditions
        for (n, alpha, beta, gamma) in self.boundary_conditions:
            glob_stiff[n, n] += alpha / beta
            glob_force[n] += gamma / beta

        # Now solve
        disp[:] = np.linalg.solve(glob_stiff, glob_force)

        self._disp[:] = disp

        # post process
        stress = np.empty(self.num_elem)
        stran = np.empty(self.num_elem)
        for elem in self.elements:
            # element nodes, coordinates, and displacement
            elem_nodes = self.conn[elem.num][:elem.num_points]
            elem_coords = self.coords[elem_nodes]
            elem_disp = disp[elem_nodes]
            elem_stran = []
            elem_stress = []

            for (n, xi) in enumerate(elem.gauss_points):
                B = elem.b_matrix(xi, elem_coords)
                e = np.dot(B, elem_disp)
                s = elem.mat.get_stress(e)
                elem_stran.append(e)
                elem_stress.append(s)
            stress[elem.num] = np.sum(elem_stress) / len(elem_stress)
            stran[elem.num] = np.sum(elem_stran) / len(elem_stran)

        self.snapshot(stress, stran, self.disp)

        return

    def iterative_solve(self):
        """Solve for the dependent variable using an iterative Newton method

        """
        u = np.zeros(self.num_node)
        du = np.zeros(self.num_node)
        for nit in range(25):

            # initialize global stiffness, force, displacement
            glob_stiff = np.zeros((self.num_node, self.num_node))
            glob_force = np.zeros(self.num_node)
            glob_resid = np.zeros(self.num_node)

            for elem in self.elements:

                # element nodes, coordinates, and displacement
                elem_nodes = self.conn[elem.num][:elem.num_points]
                elem_coords = self.coords[elem_nodes]
                elem_disp = u[elem_nodes]

                # element stiffness and force
                elem_stiff = elem.stiffness(elem_coords, elem_disp)
                elem_force = elem.force(self.dist_load, elem_coords)
                elem_resid = elem.residual(elem_coords, elem_disp)

                # Add element contribution to global force and stiffness
                for a in range(elem.num_points):
                    I = elem_nodes[a]
                    glob_force[I] += elem_force[a]
                    glob_resid[I] += elem_resid[a]
                    for b in range(elem.num_points):
                        J = elem_nodes[b]
                        glob_stiff[I, J] += elem_stiff[a, b]

            # Concentrated forces
            for (node, mag) in self.conc_forces:
                glob_force[node] += mag

            rhs = glob_force - glob_resid

            # Apply boundary conditions
            for (n, alpha, beta, gamma) in self.boundary_conditions:
                if abs(alpha - 1.) < EPS:
                    gamma = gamma - u[n]
                glob_stiff[n, n] += alpha / beta
                rhs[n] += gamma / beta

            # Now solve
            du[:] = np.linalg.solve(glob_stiff, rhs)
            u += du
            err1 = np.sqrt(np.dot(du, du))
            if err1 < TOL:
                break

        else:
            error("newton iterations failed to converge")

        self._disp[:] = u

        # post process
        stress = np.empty(self.num_elem)
        stran = np.empty(self.num_elem)
        for elem in self.elements:
            # element nodes, coordinates, and displacement
            elem_nodes = self.conn[elem.num][:elem.num_points]
            elem_coords = self.coords[elem_nodes]
            elem_disp = u[elem_nodes]
            elem_stran = []
            elem_stress = []
            for (n, xi) in enumerate(elem.gauss_points):
                B = elem.b_matrix(xi, elem_coords)
                e = np.dot(B, elem_disp)
                s = elem.mat.get_stress(e)
                elem_stran.append(e)
                elem_stress.append(s)
            stress[elem.num] = np.sum(elem_stress) / len(elem_stress)
            stran[elem.num] = np.sum(elem_stran) / len(elem_stran)
        self.snapshot(stress, stran, self.disp)

        return

    def interpolated_displacements(self):
        """Generate arrays of coordinate and interpolated displacements

        Returns
        xvals : ndarray
            Generated coordinates in domain of model
        yvals : ndarray
            Interpolated displacements corresponding to xvals

        """
        xvals = []
        yvals = []
        nat_space = np.linspace(-1, 1)
        for elem in self.elements:
            elem_nodes = self.conn[elem.num][:elem.num_points]
            elem_coords = self.coords[elem_nodes]
            elem_disp = self._disp[elem_nodes]
            for xi in nat_space:
                xvals.append(elem.mapping(xi, elem_coords))
                yvals.append(np.dot(elem_disp, elem.shape(xi)))
        return xvals, yvals

    def plot_disp(self, xlabel=None, ylabel=None, filename=None):
        """Plot the nodal displacements

        """
        import matplotlib.pyplot as plt
        if self._disp is None:
            warn("FEModel must be solved before plotting displacements")
        x, y = self.interpolated_displacements()
        plt.plot(x, y, "b-")
        plt.scatter(self.coords, self.disp)
        if xlabel:
            plt.xlabel(xlabel)
        if ylabel:
            plt.ylabel(ylabel)
        if filename:
            plt.savefig(filename)
        else:
            plt.show()

    def print_disp(self):
        """Print the nodal displacements

        """
        print "   Node    Displacement"
        for (i, u) in enumerate(self.disp):
            print "{0:=5d}        {1: .6f}".format(i+1, u)

    def snapshot(self, stress, stran, u):
        statev = []
        u = np.column_stack((u, np.zeros(self.num_node))).flatten()
        time = 1.
        dtime = 1.
        dstran = np.array(stran)
        temp = 0.
        dtemp = 0.
        elem_blk_ids = [elem_blk[0] for elem_blk in self.elem_blks]
        elems_per_block = [elem_blk[1] for elem_blk in self.elem_blks]
        self.exo.snapshot(elem_blk_ids, elems_per_block, stress,
                          statev, stran, dstran, time, dtime, temp, dtemp, u)

    @classmethod
    def create_uniform(cls, num_el, length, elem_name, mat_name, mat_props, **opts):
        """Initialize a FE Model object with a uniform mesh

        Parameters
        ----------
        num_el : int
            Number of elements
        length : real
            Domain length
        mat_name : real
            Uniform value of material property
        elem_type : object
            The element type

        Returns
        -------
        cls : object
            The instantiated FEModel

        """
        elem_type = get_elem_by_name(elem_name)
        if elem_type.order == 1:
            coords, conn = linmesh_1d(0, length, num_el)
        elif elem_type.order == 2:
            coords, conn = quadmesh_1d(0, length, num_el)
        else:
            error("unknown element order")

        # Material - a single material per element block
        mat_type = get_mat_by_name(mat_name)
        mat_type.check_props(mat_props)

        # single element block containing all elements
        num_elem = conn.shape[0]
        elems = range(num_elem)
        elem_blk = [(0, elems, elem_type, mat_type, mat_props)]
        return cls(coords, conn, elem_blk, o=0, solver=opts.get("solver"))

    @classmethod
    def create_gen(cls, *info, **opts):
        """Initialize a FE Model object with a general mesh

        Parameters
        ----------
        args : tuple
            The args[i] are 3 tuples containing for each block of the mesh:
               num_elem_in_blk, len_blk, elem_name, mat_name, mat_props
        kwargs : dict
            Passed to genmesh_1d

        """
        # gather information to be sent to genmesh_1d
        args = []
        elem_blks = []
        for (i, item) in enumerate(info):
            try:
                num_elem_in_blk, len_blk, elem_name, mat_name, mat_props = item
            except ValueError:
                error("incorrect *info sent to create_gen")
            elem_type = get_elem_by_name(elem_name)
            mat_type = get_mat_by_name(mat_name)
            mat_type.check_props(mat_props)
            args.append((num_elem_in_blk, len_blk, elem_type.name))

            # skeleton for the element blocks spec
            elem_blks.append([i, None, elem_type, mat_type, mat_props])

        # generate the mesh
        coords, conn, elems = genmesh_1d(*args)

        # finish element blocks spec
        for (i, elems_in_blk) in enumerate(elems):
            elem_blks[i][1] = elems_in_blk

        return cls(coords, conn, elem_blks, o=0, solver=opts.get("solver"))


# -------------------------------------------------------------- Element ---- #
class Element(object):
    """Base element class.

    """
    order = None
    name = None
    num_points = None
    num_dof = None
    num_gauss = None
    gauss_weights = None
    gauss_points = None
    def mapping(self, *args, **kwargs): raise NotImplementedError
    def shape(self, *args, **kwargs): raise NotImplementedError
    def shape_deriv(self, *args, **kwargs): raise NotImplementedError

    def stiffness(self, coords, u):
        """Compute the element stiffness

        Parameters
        ----------
        coords : ndarray
            Element coordinates

        Returns
        -------
        stiff : ndarray, (num_points, num_points)
            Element stiffness

        """
        # integrate stiffness by looping over Gauss points and summing contributions
        stiff = np.zeros((self.num_points, self.num_points))
        for (n, xi) in enumerate(self.gauss_points):
            weight = self.gauss_weights[n]
            jac = self.jacobian(xi, coords)
            B = self.b_matrix(xi, coords)
            stran = np.dot(B, u)
            km = self.mat.get_stiff(stran)
            ke = km * jac * weight * np.outer(B, B)
            stiff += ke

        return stiff

    def force(self, q, coords):
        """Compute the element force using Gauss quadrature

        """

        # integrate force by looping over Gauss points and summing contributions
        f = np.zeros(self.num_points)
        for (n, xi) in enumerate(self.gauss_points):
            # Gauss point and weight
            weight = self.gauss_weights[n]

            # shape function, jacobian, and distribued load
            N = self.shape(xi)
            jac = self.jacobian(xi, coords)
            qx = q(self.mapping(xi, coords))
            f += qx * N * jac * weight
        return f

    def residual(self, coords, u):
        """Compute the element residual using Gauss quadrature

        """
        # integrate element residual by looping over Gauss points and summing
        # contributions
        r = np.zeros(self.num_points)
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
        if self.order == 1 and abs((coords[1] - coords[0]) - 2. * jac) > EPS:
            warn("Incorrect Jacobian computed for element {0}".format(self.num))
        return jac

    def b_matrix(self, xi, coords):
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
    gauss_weights = np.ones(num_gauss)
    gauss_points = np.array([-1, 1], dtype=np.float64) / ROOT3
    def __init__(self, num, nodes, mat):
        self.num = num
        self.nodes = nodes
        self.mat = mat

    def mapping(self, xi, coords):
        mapp = coords[0] + .5 * (coords[1] - coords[0]) * (1. + xi)
        return mapp

    def shape(self, xi):
        """Evaluate the 1D element shape function

        """
        N = np.zeros(self.num_points)
        N[0] = 1 - xi
        N[1] = 1 + xi
        return N / 2.

    def shape_deriv(self, xi):
        """Evaluate the derivative of the element shape function

        """
        dNdxi = np.zeros(self.num_points)
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

    def __init__(self, num, nodes, mat):
        self.num = num
        self.nodes = nodes
        self.mat = mat

    def mapping(self, xi, coords):
        return np.dot(self.shape(xi), coords)

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


def get_elem_by_name(elem_name):
    """Return the element class associated with elem_name

    Parameters
    ----------
    elem_name : str
        The element name

    Returns
    -------
    elem_class : object
        The uninstantiated element class

    """
    elements = (LinearElement, QuadraticElement)
    for element in elements:
        if element.name.lower() == elem_name.lower():
            return element
    error("element name {0} unrecognized".format(elem_name))


# ------------------------------------------------------------- Material ---- #
class Material(object):
    name = None
    @classmethod
    def check_props(self, *args, **kwargs): raise NotImplementedError
    def get_stress(self, *args, **kwargs): raise NotImplementedError


class LinearElastic(Material):
    name = "elastic"
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


if __name__ == "__main__":
    # compare the finite element solution with the analytic solution
    import sympy as sp
    import matplotlib.pyplot as plt

    # FE model
    num_el = 2
    length = 1.
    elem_name = "Link2"
    mat_name = "elastic"
    mat_props = [1.]
    model = FEModel.create_uniform(num_el, length, elem_name, mat_name, mat_props,
                                   solver="iter")
    func = lambda x: -1. * np.sin(x)
    model.assign_distributed_load(func)
    # model.assign_conc_force(length/2.+.01*length, -.03, placement="coord")
    # model.assign_conc_force(num_el/2, -.03)
    model.assign_bc("ilo", "essential", 0.)
    model.assign_bc("ihi", "essential", 0.)
    model.solve()
    model.plot_disp(xlabel=r"$x$ (L)", ylabel=r"$u$ (L)", filename="fe_result.pdf")

    # Analytic
    x = sp.Symbol("x")
    u = sp.Function("u")
    q = -sp.sin(x)
    sol = sp.dsolve(sp.diff(u(x), x, x) + q).rhs
    coeffs = sp.solve([sol.subs({x: 0}), sol.subs({x: 1})])
    sol = sol.subs(coeffs)
    xvals = np.linspace(model.coords[0], model.coords[-1])
    sol = np.array([sol.subs(x, xval).evalf() for xval in xvals])
    plt.cla()
    plt.clf()
    plt.plot(xvals, sol, "r-", lw=2, label="Analytic")
    x, y = model.interpolated_displacements()
    plt.plot(x, y, "b-", label="Finite Element")
    plt.plot(model.coords, model.disp, "b.")
    plt.legend(loc="best")
    #    plt.show()
