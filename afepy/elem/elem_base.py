from math import sqrt
from numpy import dot, zeros, zeros_like, eye, array, sum as asum, float64
from numpy.linalg import inv, det
from tools.misc import getopt, dist
from tools.errors import AFEPYError
from tools.datastructs import ARRAY, SYMTEN, Variable
import mesh.geom as geom

class MetaClass(type):
    """metaclass which overrides the "__call__" function"""
    def __call__(cls, *args, **kwargs):
        """Called when you call Class()

        """
        obj = type.__call__(cls)
        if args:
            obj.initialize(*args, **kwargs)
        obj.setopts(**kwargs)
        return obj

class ContinuumElement(object):
    """Base class for an element.

    """
    __metaclass__ = MetaClass

    def initialize(self, elem_id, elem_nodes, material, **kwargs):

        self.elem_id = elem_id
        self.elem_nodes = elem_nodes
        self.density = kwargs.get("density", 1.)
        self.material = material

        # register required variables
        self.variables = []
        self.variables.append(Variable("STRESS", SYMTEN, None, None))
        self.variables.append(Variable("STRAIN", SYMTEN, None, None))
        self.variables.append(Variable("DSTRAIN", SYMTEN, None, None))
        elem_var_names = [v.name for v in self.variables]
        for v in material.variables:
            if v.name in elem_var_names:
                ev = self.variables[elem_var_names.index(v.name)]
                if v.type == ev.type:
                    continue
                raise AFEPYError("duplicate variable {0}".format(v.name))
            self.variables.append(v)

    def setopts(self, **kwargs):
        pass

    def face_nodes(self, face_num):
        return geom.face_nodes(self.num_coord, self.num_node, face_num)

    def jacobian(self, X, xi=None):
        """Element Jacobian

        1. Shape function derivative at Gauss points
            dNdxi = self.lgrad(xi)

        2. Compute the Jacobian matrix J = dNdxi.x
           dxdxi = dot(dNdxi, X)
           J = det(dxdxi)
        """
        a = lambda _: det(dot(self.shape.grad(_), X))
        if xi is not None:
            return a(xi)
        return array([a(xi) for xi in self.integration.points])

    def grad(self, X):
        """Shape function derivatives with respect to global coordinates

        1. shape function derivative at Gauss points
           dNdxi = self.lgrad(xi)
           dxdxi = dot(dNdxi, X)

        2. Convert shape function derivatives to derivatives
           wrt global X
           dxidx = inv(dxdxi)
           dNdx = dot(dxidx, dNdxi)
        """
        a = lambda _: self.shape.grad(_)
        b = lambda _: inv(dot(a(_), X))
        return array([dot(b(xi), a(xi)) for xi in self.integration.points])

    def update_material(self, data, time, dtime, x, npt, kstep):
        ntens = self.ndi + self.nshr
        temp = None
        dtemp = None
        energy = None
        F0 = None
        F = None
        elec_field = None
        user_field = None
        return self.material(time, dtime, temp, dtemp, energy, F0, F,
                             data.strain, data.dstrain, elec_field, user_field,
                             self.ndi, self.nshr, ntens, x, self.elem_id, npt,
                             kstep, data.stress, data.statev)

    def integrate2(self, fdata, time, dtime, X, u, kstep):
        """Assemble the element stiffness

        Parameters
        ----------

        Returns
        -------
        A : ndarray (ndof, ndof)
            A is changed in place

        """
        # compute integration point data
        x = X + u
        shg = self.grad(X)
        det = self.jacobian(X)
        w = self.integration.weights
        shgbar = self.mean_shg(w, det, shg)
        Q = zeros((self.num_dof_per_node * self.num_node,
                   self.num_dof_per_node * self.num_node))
        for (npt, xi) in enumerate(self.integration.points):

            # Update material state
            B = self.b_matrix(shg[npt], shgbar)

            # tjfulle, here I would replace
            D = self.update_material(fdata[npt], time, dtime, x, npt, kstep)

            # Add contribution of function call to integral
            Q[:] += dot(dot(B.T, D), B) * det[npt] * w[npt]

        return Q

    def integrate(self, fdata, X, u):
        """

        Parameters
        ----------

        Returns
        -------

        """
        R = zeros(self.num_dof_per_node * self.num_node)

        # compute integration point data
        x = X + u
        shg = self.grad(X)
        det = self.jacobian(X)
        w = self.integration.weights

        for (npt, xi) in enumerate(self.integration.points):
            B = self.b_matrix(shg[npt])
            R[:] += dot(fdata[npt].stress, B) * det[npt] * w[npt]

        return R

    def integrate_bndry(self, X, trac_vec):
        """Apply the Von Neumann (natural) BC to the element

        Von Neummann BC is applied as a surface load on element faces.

        Parameters
        ----------
        X : array_like
            Current nodal coords (of face nodes)

        trac_vec : array_like
            Tractions
            trac_vec[i] -> traction on coordinate i as a function of time

        Returns
        -------
        r : array_like
            Element distributed load vector

        """
        r = zeros((self.num_dof_per_node * self.num_face_nodes))
        w = self.bndry.integration.weights
        for (npt, xi) in enumerate(self.bndry.integration.points):

            # Compute shape functions and derivatives wrt local coords
            N = self.bndry.eval(xi)
            dNdxi = self.bndry.grad(xi)
            dxdxi = dot(dNdxi, X)

            if self.num_coord == 2:
                det = sqrt(dxdxi[0, 0] ** 2 + dxdxi[0, 1] ** 2)

            elif self.num_coord == 3:
                a = (dxdxi[0, 1] * dxdxi[1, 2]) - (dxdxi[1, 1] * dxdxi[0, 2])
                b = (dxdxi[0, 0] * dxdxi[1, 2]) - (dxdxi[1, 0] * dxdxi[0, 2])
                c = (dxdxi[0, 0] * dxdxi[1, 1]) - (dxdxi[1, 0] * dxdxi[0, 1])
                det = sqrt(a ** 2 + b ** 2 + c ** 2)

            for a in range(self.num_face_nodes):
                for i in range(self.num_dof_per_node):
                    row = self.num_dof_per_node * a + i
                    traction = N[a] * trac_vec[i]
                    r[row] += traction * w[npt] * det

        return r

    def mean_shg(self, w, det, shg):
        el_vol = dot(det, w)
        shgbar = zeros_like(shg[0])
        for (npt, xi) in enumerate(self.integration.points):
            # Compute the integrals over the volume
            fac = w[npt] * det[npt] / self.num_coord / el_vol
            for a in range(self.num_node):
                for i in range(self.num_dof_per_node):
                    shgbar[i, a] += shg[npt, i, a] * fac
        return shgbar

    def interpolate_to_centroid(self, fdata):
        """Inverse distance weighted average of integration point data at the
        element centroid"""
        return self.average(self.cp, fdata)

    def project_to_nodes(self, fdata, v):
        """Inverse distance weighted average of integration point data at each
        element node"""
        nx = len(v)
        a = zeros((self.num_node, nx))
        for i in range(self.num_node):
            a[i,:] = self.average(self.xp[i], fdata, v)
        return a

    def average(self, point, fdata, v=None):
        """Inverse distance weighted average of integration point data at point"""
        if v is None:
            v = range(len(fdata[0].data))
        nx = len(v)
        ave = zeros(nx)
        w = []
        for (i, xi) in enumerate(self.integration.points):
            d = max(dist(point, xi), 1E-06)
            w.append(1. / d)
            ave[:] += [fdata[i][v][x] * w[-1] for x in range(nx)]
        ave /= asum(w)
        return ave

    def mass(self, X, lumped_mass=0):
        shg = self.grad(X)
        mel = zeros((self.num_dof_per_node*self.num_node,
                     self.num_dof_per_node*self.num_node))
        w = self.integration.mass_weights
        rho = self.density

        #  Loop over the integration points
        for (npt, xi) in enumerate(self.integration.mass_points):

            # Compute shape functions and derivatives wrt local coords
            N = self.shape.eval(xi)
            dNdxi = self.shape.grad(xi)
            dxdxi = dot(dNdxi, X)
            jac = det(dxdxi);

            for a in range(self.num_node):
                for b in range(self.num_node):
                    for i in range(self.num_dof_per_node):
                        row = self.num_dof_per_node * a + i
                        col = self.num_dof_per_node * b + i
                        mel[col, row] += rho * N[b] * N[a] * w[npt] * jac

        # Evaluate a lumped mass matrix using the row sum method
        if lumped_mass:
            for a in range(self.num_node * self.num_dof_per_node):
                m = asum(mel[a, :])
                mel[a, :] = 0
                mel[a, a] = m

        return mel
