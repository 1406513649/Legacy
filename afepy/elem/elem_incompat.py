from numpy import dot, zeros, zeros_like
from numpy.linalg import inv, det

from elem_base import ContinuumElement

class ContinuumElementI(ContinuumElement):

    def integrate2(self, fdata, time, dtime, X, u, kstep):
        """Integrate the stiffness using incompatible modes"""

        # see base class implementation for comments
        x = X + u
        shg = self.grad(X)
        det = self.jacobian(X)
        w = self.integration.weights

        # incompatible modes stiffnesses
        n = self.num_incompat_modes * self.num_incompat_modes
        Q = zeros((self.num_dof_per_node * self.num_node,
                   self.num_dof_per_node * self.num_node))
        kda = zeros((self.num_dof_per_node*self.num_node,
                     self.num_coord*self.num_dof_per_node))
        kaa = zeros((self.num_coord*self.num_dof_per_node,
                     self.num_coord*self.num_dof_per_node))
        kdd = zeros_like(Q)

        for (npt, xi) in enumerate(self.integration.points):
            B, G = self.b_matrix(shg[npt], shgbar=None, coords=x,
                                 lcoords=xi, det=det[npt], disp=1)
            D = self.material(fdata[npt], time, dtime, x, self.elem_id,
                              npt, kstep, self.ndi, self.nshr)

            # Add contribution of function call to integral
            kdd[:] += dot(dot(B.T, D), B) * det[npt] * w[npt]
            kda[:] += dot(dot(B.T, D), G) * det[npt] * w[npt]
            kaa[:] += dot(dot(G.T, D), G) * det[npt] * w[npt]

        Q[:] = kdd  - dot(dot(kda, inv(kaa)), kda.T)
        return Q
