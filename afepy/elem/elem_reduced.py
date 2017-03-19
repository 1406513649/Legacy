from numpy import zeros, zeros_like, dot

from elem_base import ContinuumElement
from tools.misc import getopt

class ContinuumElementR(ContinuumElement):

    def setopts(self, **elem_opts):
        self.hgstiff = getopt("hourglass stiffness", elem_opts)
        if self.hgstiff is None:
            self.hgstiff = self.material.hourglass_stiffness

    def integrate2(self, fdata, time, dtime, X, u, kstep):
        """Modify the stiffness by including hourglass stiffness

        """
        Q = super(ContinuumElementR, self).integrate2(fdata, time,
                                                      dtime, X, u, kstep)

        # perform hourglass correction
        hgstiff = zeros_like(Q)
        shg = self.grad(X)
        det = self.jacobian(X)
        w = self.integration.weights
        for (npt, xi) in enumerate(self.hgpoints):

            # hourglass base vectors
            g = self.hgvec[npt]

            for i in range(len(xi)):
                xi[i] = dot(g, X[:, i])

            # correct the base vectors to ensure orthogonality
            scale = 0.
            for a in range(self.num_node):
                for i in range(self.num_coord):
                    g[a] -= xi[i] * shg[npt,i,a]
                    scale += shg[npt,i,a] * shg[npt,i,a]
            scale *= self.hgstiff

            for a in range(self.num_node):
                for i in range(self.num_dof_per_node):
                    for b in range(self.num_node):
                        for j in range(self.num_dof_per_node):
                            k = self.num_dof_per_node * a + i
                            l = self.num_dof_per_node * b + j
                            hgstiff[k, l] += scale * g[a] * g[b] * det[npt] * 4.

        Q[:] += hgstiff

        return Q
