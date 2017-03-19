import numpy as np
from collections import OrderedDict
from tools.logger import ConsoleLogger as logger
from tools.errors import AFEPYError
from source_term import SourceTerm
from bc import bcsum
np.set_printoptions(2)

class ElementBlock(OrderedDict):
    pass

class FiniteElementSpace(object):

    def __init__(self, mesh, dict):

        if not mesh.blocks:
            # look for speciall block 'All' in dict
            if len(dict) == 1 and dict.keys()[0].lower() == "all":
                key = dict.keys()[0]
                mesh.ElementBlock(name=key, elements="all")

        self.elements = np.empty(mesh.num_cell, dtype=np.object)
        self.num_elem = mesh.num_cell
        self.blocks = []
        for eb in mesh.blocks.values():
            self.blocks.append(ElementBlock())
            self.blocks[-1].__dict__.update(eb.__dict__)
        self.connect = mesh.connect

        mesh.run_diagnostics()
        self.mesh = mesh

        # assign properties to elements and determine if all blocks have been
        # assigned properties
        unassigned = []
        self.elems_per_block = []
        for eb in self.blocks:
            try:
                elem = dict[eb.name]
            except KeyError:
                unassigned.append(eb.name)
                continue

            for elem_id in eb.elem_ids:
                elem_nodes = [n for n in self.mesh.connect[elem_id] if n >= 0]
                self.elements[elem_id] = elem(elem_id, elem_nodes)

            eb.num_int_point = self.elements[elem_id].integration.num_point
            eb.elem_type = self.elements[elem_id].type
            eb.num_node_per_elem = self.elements[elem_id].num_node
            eb.num_dof_per_node = self.elements[elem_id].num_dof_per_node
            eb.ndi = self.elements[elem_id].ndi
            eb.nshr = self.elements[elem_id].nshr
            self.elems_per_block.append(eb.elem_ids)

        if unassigned:
            u = ", ".join(unassigned)
            raise AFEPYError("Element block without properties detected.  "
                             "All element blocks must be assigned properties.  "
                             "Unassigned element blocks:\n {0}".format(u))

        # determine total number of dofs, look for conflicting nodes
        node_dofs = {}
        for e in self.elements:
            node_ids = [n for n in self.mesh.connect[e.elem_id] if n >= 0]
            n = self.elements[e.elem_id].num_dof_per_node
            for node_id in node_ids:
                try:
                    nn = node_dofs[node_id]
                    if nn == n:
                        continue
                    raise AFEPYError("conflicting dofs in node "
                                     "{0}".format(node_id))
                except KeyError:
                    node_dofs[node_id] = n
        self.num_dof = sum(node_dofs.values())

        self.num_dof_per_node = self.elements[0].num_dof_per_node
        self.mesh.num_dof_per_node = self.num_dof_per_node
        self.elem_blk_ids = self.mesh.elem_blk_ids
        self.num_dim = self.mesh.num_dim
        self.num_node = self.mesh.num_node
        self.X = self.mesh.coords
        self.dofs = np.arange(self.num_dof).reshape(self.mesh.num_node, -1)

    def __getattr__(self, key):
        """Return attribute to FiniteElementSpace instance. If it doesn't
        exist in self.__dict__, look for it in this instances mesh

        """
        try:
            return self.__dict__[key]
        except KeyError:
            try:
                return getattr(self.mesh, key)
            except KeyError:
                raise AttributeError("'FiniteElementSpace' object has no "
                                     "attribute {0}".format(repr(key)))

    def update_kinematics(self, data, u, dtime=1.):
        """Update kinematic quantities to end of step

        """
        # loop over each block and update dstrain, strain at each integration
        # point at each element
        for (iblk, elems_this_blk) in enumerate(self.elems_per_block):

            for (iel, e) in enumerate(self.elements[elems_this_blk]):

                # displacement of element
                u_e = np.zeros_like(self.X[e.elem_nodes])

                for a in range(e.num_node):
                    row = e.num_dof_per_node * self.connect[e.elem_id, a]
                    rows = [row + i for i in range(e.num_dof_per_node)]
                    u_e[a, :] = u[rows]
                X = self.X[e.elem_nodes]
                x = X + u_e

                # compute integration point data
                shg = e.grad(X)
                det = e.jacobian(X)
                w = e.integration.weights
                shgbar = e.mean_shg(w, det, shg)

                for (npt, xi) in enumerate(e.integration.points):

                    # Assemble B matrix.
                    B = e.b_matrix(shg[npt], shgbar)

                    # strain increment
                    de = np.dot(B, u_e.flatten())
                    data.blk_data[iblk][1, iel, npt].dstrain[:] = de

                    # strain
                    eps = data.blk_data[iblk][0, iel, npt].strain[:] + de
                    data.blk_data[iblk][1, iel, npt].strain[:] = eps

        return

    def update_material(self, data, u, time=0., dtime=1., kstep=0):
        """Loop through elements in this block, update state, and add the
        element contribution to the global stiffness and, optionally, the
        global residual

        Parameters
        ----------

        Returns
        -------

        """
        for (iblk, elems_this_blk) in enumerate(self.elems_per_block):
            for (iel, e) in enumerate(self.elements[elems_this_blk]):
                X = self.X[e.elem_nodes, :]
                u_e = np.zeros((e.num_node, e.num_dof_per_node))
                for a in range(e.num_node):
                    row = e.num_dof_per_node * self.connect[e.elem_id, a]
                    rows = [row + i for i in range(e.num_dof_per_node)]
                    u_e[a, :e.num_dof_per_node] = u[rows]
                x = X + u_e
                fdata = data.blk_data[iblk][1, iel]
                for (npt, xi) in enumerate(e.integration.points):
                    # call the material model at this integraton point
                    e.update_material(fdata[npt], time, dtime, x,
                                      npt, kstep)

        return

    def stiffness(self, data, u=None, time=0., dtime=1., kstep=0):
        """Loop through elements in this block, update state, and add the
        element contribution to the global stiffness and, optionally, the
        global residual

        Parameters
        ----------

        Returns
        -------

        """
        if u is None:
            u = np.zeros(self.num_dof)

        # zero stiffness
        A = np.zeros((self.num_dof, self.num_dof))

        for (iblk, elems_this_blk) in enumerate(self.elems_per_block):

            # Update the model state and add contributions to global stiffness
            for (iel, e) in enumerate(self.elements[elems_this_blk]):

                # current coordinates of element
                X = self.X[e.elem_nodes, :]
                u_e = np.zeros((e.num_node, e.num_dof_per_node))
                for a in range(e.num_node):
                    row = e.num_dof_per_node * self.connect[e.elem_id, a]
                    rows = [row + i for i in range(e.num_dof_per_node)]
                    u_e[a, :e.num_dof_per_node] = u[rows]

                # Allocate storage for this element's stiffness
                fdata = data.blk_data[iblk][1, iel]
                stiff = e.integrate2(fdata, time, dtime, X, u_e, kstep)

                # Assemble global stiffness
                # Scatter operation.
                elem_dofs = self.dofs[e.elem_nodes].flatten()
                A[np.ix_(elem_dofs, elem_dofs)] += stiff

        return A

    def residual(self, data, u):
        """Loop through elements in this block, update state, and add the
        element contribution to the global stiffness and, optionally, the
        global residual

        Parameters
        ----------

        Returns
        -------
        R is changed in place

        """
        R = SourceTerm(self)
        for (iblk, elems_this_blk) in enumerate(self.elems_per_block):

            # Update the model state and add contributions to global stiffness
            for (iel, e) in enumerate(self.elements[elems_this_blk]):

                # current coordinates of element
                X = self.X[e.elem_nodes, :]
                u_e = np.zeros((e.num_node, e.num_dof_per_node))
                for a in range(e.num_node):
                    row = e.num_dof_per_node * self.connect[e.elem_id, a]
                    rows = [row + i for i in range(e.num_dof_per_node)]
                    u_e[a, :e.num_dof_per_node] = u[rows]

                fdata = data.blk_data[iblk][1, iel]
                resid = e.integrate(fdata, X, u_e)

                # Assemble global stiffness
                # Scatter operation.
                elem_dofs = self.dofs[e.elem_nodes].flatten()
                R[elem_dofs] += resid

        return R

    def force(self, neumann_bcs):
        Q = SourceTerm(self)
        logger.debug("applying traction boundary conditions...", end=" ")
        for (elem_id, face, components) in bcsum(neumann_bcs):
            elem = self.elements[elem_id]
            face_nodes = elem.face_nodes(face)
            x = [elem.elem_nodes[face_node] for face_node in face_nodes]
            face_dofs = self.dofs[x].flatten()

            # Coordinates of the nodes on the appropriate element face
            coord_face = np.zeros((elem.num_face_nodes, self.num_dof_per_node))
            for a in range(elem.num_face_nodes):
                # global node number
                node_num = elem.elem_nodes[face_nodes[a]]
                coord_face[a, :] = self.X[node_num, :]

            elem_trac = elem.integrate_bndry(coord_face, components)

            # Put in to the global load vector
            Q[face_dofs] += elem_trac

        logger.debug("done")
        return Q

    def apply_bcs(self, data, disp_bcs, A, b, du=None, M=None, fac=1.):

        logger.debug("applying displacement boundary conditions...", end=" ")

        if du is None:
            du = np.zeros(self.num_dof)

        for (node_id, dof, mag) in bcsum(disp_bcs):

            # Modify rows and columns of K
            if dof > self.num_dof_per_node:
                raise AFEPYError("incorrect dof")

            row = int(self.num_dof_per_node * node_id + dof)

            # current value of displacement
            u_cur = data[row] + du[row]
            ufac = fac * mag - u_cur

            # Modify the RHS
            b -= [A[i, row] * ufac for i in range(self.num_dof)]

            #  modify stiffness
            A[row, :] = 0.
            A[:, row] = 0.
            A[row, row] = 1.

            if M is not None:
                M[row, :] = 0.
                M[:, row] = 0.
                M[row, row] = 1.

            b[row] = ufac

        logger.debug("done")
        return

    def mass(self, lumped_mass=0):
        M = np.zeros((self.num_dof, self.num_dof))
        for (iblk, elems_this_blk) in enumerate(self.elems_per_block):

            # Update the model state and add contributions to global stiffness
            for (iel, e) in enumerate(self.elements[elems_this_blk]):

                # current coordinates of element
                X = self.X[e.elem_nodes, :]

                # Allocate storage for this element's stiffness
                mel = e.mass(X, lumped_mass=lumped_mass)

                # Assemble global stiffness
                # Scatter operation.
                elem_dofs = self.dofs[e.elem_nodes].flatten()
                M[np.ix_(elem_dofs, elem_dofs)] += mel

        return M

    def get_node_ids(self, nodes, nodeset, region):
        return self.mesh.get_node_ids(nodes, nodeset, region)

# --- Procedures for slow_assembly
def slow_assemble_stiff(num_el_node, num_dof_per_node, elem_nodes, stiff, A):
    for a in range(num_el_node):
        for i in range(num_dof_per_node):
            for b in range(num_el_node):
                for j in range(num_dof_per_node):
                    II = num_dof_per_node * elem_nodes[a] + i
                    JJ = num_dof_per_node * elem_nodes[b] + j
                    ii = num_dof_per_node * a + i
                    jj = num_dof_per_node * b + j
                    A[II, JJ] += stiff[ii, jj]

def slow_assemble_resid(num_el_node, num_dof_per_node, elem_nodes, resid, R):
    for a in range(num_el_node):
        for i in range(num_dof_per_node):
            row = num_dof_per_node * elem_nodes[a] + i
            R[row] += resid[num_dof_per_node * a + i]

def slow_assemble_trac(num_face_nodes, num_dof_per_node, elem_nodes,
                       face_nodes, elem_trac, glob_force):
    for a in range(num_face_nodes):
        for i in range(num_dof_per_node):
            row = elem_nodes[face_nodes[a]] * num_dof_per_node + i
            glob_force[row] += elem_trac[a * num_dof_per_node + i]
