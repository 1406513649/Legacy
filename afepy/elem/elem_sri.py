from numpy import outer, zeros, dot, array, sum as asum
from elem_base import ContinuumElement

class ContinuumElementSRI(ContinuumElement):

    def integrate2(self, fdata, time, dtime, X, u, kstep):
        # see base class implementation for comments
        Q = zeros((self.num_dof_per_node * self.num_node,
                   self.num_dof_per_node * self.num_node))

        # make a copy of the element data for use below
        x = X + u
        copy = [fdata[i].copy() for i in range(self.integration.num_point)]

        shg = self.grad(X)
        det = self.jacobian(X)
        w = self.integration.weights
        for (npt, xi) in enumerate(self.integration.points):
            B = self.b_matrix(shg[npt])

            # tjfulle: now we need to fix this up to send in the strain
            # increment associated with sri_e
            D = self.update_material(fdata[npt], time, dtime, x, npt, kstep)

            # selectively reduced integration. Replace D with its
            # deviatoric part. Later, the isotropic part will be
            # contributed to the element stiffness using reduced
            # integration.
            D -= self.iso_contrib(D, self.num_coord, self.nshr)

            # Add contribution of function call to integral
            Q[:] += dot(dot(B.T, D), B) * det[npt] * w[npt]

        # perform the additional dilatational integration
        self.sri_e.ndi = self.ndi
        self.sri_e.nshr = self.nshr
        self.sri_e.elem_id = self.elem_id
        w = self.sri_e.integration.weights
        det = self.sri_e.jacobian(X)
        shg = self.sri_e.grad(X)

        sri_data = fdata[0].copy()
        for (npt, xi) in enumerate(self.sri_e.integration.points):

            # average element quantities at this point
            sri_data.data[:] = self.average(xi, fdata)

            # Evaluate the material
            D = self.update_material(sri_data, time, dtime, x, npt, kstep)

            # Add contribution of function to integral
            B = self.sri_e.b_matrix(shg[npt])
            Diso = self.iso_contrib(D, self.num_coord, self.nshr)
            Q[:] += dot(dot(B.T, Diso), B) * det[npt] * w[npt]

        return Q
