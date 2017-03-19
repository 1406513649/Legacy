from math import sqrt
from numpy import dot, zeros, zeros_like, eye, array, sum as asum, float64, trace
from numpy.linalg import inv, det
from tools.misc import getopt, dist
from tools.errors import AFEPYError
from tools.datastructs import AttrArray, ARRAY, SYMTEN
import mesh.geom as geom
from elem_base import ContinuumElement

class ContinuumElementH(ContinuumElement):
    """Base class for a hypbrid element.

    """
    def integrate2(self, fdata, time, dtime, X, u, kstep):
        """Assemble the element stiffness """

        # compute integration point data
        x = X + u
        shg = self.grad(X)
        det = self.jacobian(X)
        w = self.integration.weights
        Q = zeros((self.num_dof_per_node * self.num_node + self.num_press,
                   self.num_dof_per_node * self.num_node + self.num_press))
        for (npt, xi) in enumerate(self.integration.points):

            # Update material state
            B = self.b_matrix(shg[npt], shgbar=None)

            D = self.material(fdata[npt], time, dtime, x, self.elem_id,
                              npt, kstep, self.ndi, self.nshr)

            #
            K = trace(D) / self.num_coord / self.num_coord

            # Add contribution of function call to integral
            Q[:] += dot(dot(B.T, D), B) * det[npt] * w[npt]
            Q[:] -= K * dNdx(b,k) * dNdx(a,i) * w[npt] * det[npt]

        return Q

    def integrate(self, fdata, X, u):
        """

        Parameters
        ----------

        Returns
        -------

        """
        R = zeros(self.num_dof_per_node * self.num_node + self.num_press)

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
