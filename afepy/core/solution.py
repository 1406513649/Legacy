import numpy as np
from tools.datastructs import BlockData

class SolutionSpace:
    def __init__(self, V):

        self.time = 0.
        self.time_p = 0.
        self.dtime = 0.
        self.V = V
        self.count = 0

        # dependent variable
        self.u_p = np.zeros(V.num_dof)
        self.u = np.zeros(V.num_dof)
        self._snapshots = []

        self.blk_data = []
        for eb in V.blocks:
            d = BlockData(V.elements[eb.elem_ids])
            self.blk_data.append(d)

        self.num_node = self.V.num_node
        self.ndofn = self.V.num_dof_per_node
        self.num_dim = self.V.num_dim

        s = "Displacement"
        self.default_node_vars = [s + "%s" %(x) for x in "xyz"[:self.ndofn]]
        self.node_output_vars = [x for x in self.default_node_vars]
        self.node_var_indices = []

    def __iadd__(self, du):
        self.advance_data(du)
        return self

    def __getitem__(self, i):
        return self.u[i]

    def reset(self):
        self.u = np.array(self.u_p)
        for d in self.blk_data:
            d.reset()

    def advance_data(self, du):
        self.u_p = np.array(self.u)
        self.u += du
        self.dtime = self.time - self.time_p
        self.time_p = self.time
        for d in self.blk_data:
            d.advance()
        data = [bd[0].copy() for bd in self.blk_data]
        self._snapshots.append([self.time, self.dtime, data, self.u.copy()])

    def snapshots(self, count=None):
        node_data = np.zeros((self.num_node, len(self.node_output_vars)))
        for (t, dt, bd, u) in self._snapshots:
            ave = self.average(bd)
            node_data[:, :self.ndofn] = u.reshape(self.num_node, -1)
            if self.node_var_indices:
                v = self.node_var_indices
                node_data[:, self.ndofn:] = self.project_to_nodes(bd, v)
            yield ave, node_data, t, dt

        # reset node output
        self.node_var_indices = []
        self.node_output_vars = [x for x in self.default_node_vars]
        return

    def output(self, node=None):
        if node is None:
            return self

        if not isinstance(node, (list, tuple)):
            node = [node]

        node_vars = []
        keys = self.blk_data[0].keys
        for item in node:
            if item == "stress":
                node_vars.extend([k for k in keys if k.startswith("Stress_")])
            elif item == "strain":
                node_vars.extend([k for k in keys if k.startswith("Strain_")])
            else:
                node_vars.append(item)
        self.node_var_indices = [keys.index(k) for k in node_vars]
        self.node_output_vars.extend(node_vars)

        return self

    @property
    def genesis(self):
        elem_blks = []
        elem_data = []

        ave = []
        for (i, elem_blk) in enumerate(self.V.blocks):
            neeb = elem_blk.num_elem
            evn = self.blk_data[i].keys
            elem_blks.append([elem_blk.exo_id, elem_blk.elem_ids,
                              elem_blk.elem_type,
                              elem_blk.num_node_per_elem, evn])

            # ave.append([])
            # elems_this_blk = self.V.elems_per_block[i]
            # blkdata = self.blk_data[i].data
            # for (iel, e) in enumerate(self.V.elements[elems_this_blk]):
            #     print blkdata[iel][0][0][:]
            #     ave[i].append(e.interpolate_to_centroid(blkdata[iel]))
            # ave = np.array(ave)
            # print ave.shape
            # print (nneb, len(evn))
            # exit()
            elem_data.append([elem_blk.exo_id, neeb,
                              np.zeros((neeb, len(evn)))])
            i += 1

        nodesets = self.V.mesh.nodesets_exo
        sidesets = self.V.mesh.sidesets_exo

        elem_num_map = self.V.mesh.elem_num_map_exo

        node_vars = np.array(self.node_output_vars)
        node_data = (node_vars, np.zeros((self.num_node, node_vars.size)))
        return (self.num_dim, self.V.X, self.V.connect, elem_blks,
                nodesets, sidesets, None, elem_data, elem_num_map, node_data)

    def average(self, blk_data):
        """Loop through elements in this block, update variables, and compute the
        element averages

        Parameters
        ----------
        elements : ndarray of objects (num_elem_in_blk,)
            Instantiated elements in block
        stress : ndarray (num_elem_in_blk, 2, max_gauss, ntens)
            Stress arrays

        """
        ave = []
        for (iblk, elems_this_blk) in enumerate(self.V.elems_per_block):
            ave.append([])
            blkdata = blk_data[iblk]
            for (iel, e) in enumerate(self.V.elements[elems_this_blk]):
                ave[iblk].append(e.interpolate_to_centroid(blkdata[iel]))
            ave[iblk] = np.array(ave[iblk])
        return ave

    def project_to_nodes(self, blk_data, v):
        """Project data to nodes via lumped projection

        """
        nx = len(v)
        a = np.zeros((self.V.mesh.num_node, nx))
        dt = np.zeros(self.V.mesh.num_node)
        for (iblk, elems_this_blk) in enumerate(self.V.elems_per_block):
            blkdata = blk_data[iblk]
            for (iel, e) in enumerate(self.V.elements[elems_this_blk]):
                a[e.elem_nodes] += e.project_to_nodes(blkdata[iel], v)
                dt[e.elem_nodes] += 1
        a = (a.T / dt).T
        return a

    def Zeros(self):
        return np.zeros_like(self.u)
