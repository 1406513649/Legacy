import os
import sys
import numpy as np
import datetime

from exojac import ExodusIIFile as ExoFile

class ExodusIIFile:
    def __init__(self, filename):
        self.exo = ExodusIIManager(filename)

    def __lshift__(self, u):
        self.exo.put_init(*u.genesis)

        # Compute element averages to write to the database
        for snapshot in u.snapshots():
            self.exo.snapshot(*snapshot)
        self.exo.finish()

class ExodusIIManager(object):
    """The main ExodusII manager

    """
    def __init__(self, filename):
        self.filename = filename
        pass

    def put_init(self, num_dim, coords, conn, elem_blks,
                 node_sets, side_sets, all_glob_data, all_element_data,
                 elem_num_map, node_data, title=None, d=None):
        """Put initial data in to the ExodusII file

        num_dim : int
            Number of spatial dimensions of problem
        coords : array_like, (num_node, 3)
            Coordinates of the num_nodeth node
        conn : array_like
            Connectivity array
        elem_blks : array_like, (num_elem_blk, 5)
            Element block information
            elem_blks[i] -> [ID, [ELS IN BLK], ETYPE, NNODES]
        node_sets : array_like, (num_node_sets, 3)
            Node set information
            node_sets[i] -> [ID, NODE LIST]
        side_sets : array_like, (num_side_sets, 3)
            Side set information
            side_sets[i] -> [ID, ELEM LIST, SIDE LIST]
        all_element_data : list
            Initial data for each element
            all_element_data[i]:
              0 -> element block id
              1 -> number of elements in block
              2 -> element block data
                   element block data is of the form:
                   data[k] -> average element data for kth element
        elem_num_map : ndarray
            Element number map.  0 based indexing.
        title : str, optional [None]
            Optional title
        d : str, optional [None]
            The analysis directory

        Notes
        -----
        This function differs from the ExodusII API namesake by the
        elem_num_map title, and d paramters.

        """
        # create new file
        self.num_dim = num_dim
        self.exofile = ExoFile(self.filename, mode="w", d=d)

        # initialize file with parameters
        self.elem_blks = elem_blks
        self.elem_blk_ids = [eb[0] for eb in elem_blks]
        self.num_nodes = coords.shape[0]
        self.num_elem = conn.shape[0]
        self.num_elem_blk = len(self.elem_blks)
        num_node_sets = len(node_sets)
        num_side_sets = len(side_sets)
        if not title:
            title = "FEM {0} simulation".format(str(self.num_dim) + "D")

        self.exofile.put_init(title, self.num_dim, self.num_nodes, self.num_elem,
                              self.num_elem_blk, num_node_sets, num_side_sets)

        # write nodal coordinates values and names to database
        s = "Coord"
        coord_names = np.array([s + "%s" %(x) for x in "xyz"[:num_dim]])
        self.exofile.put_coord_names(coord_names)
        z = np.zeros(self.num_nodes) if num_dim <= 2 else coords[:, 2]
        self.exofile.put_coord(coords[:, 0], coords[:, 1], z)

        # write element order map
        self.exofile.put_elem_num_map(elem_num_map)

        # write element block parameters
        for item in self.elem_blks:
            (elem_blk_id, elem_blk_els, elem_type,
             num_nodes_per_elem, ele_var_names) = item
            # for now, we do not use attributes
            num_attr = 0
            num_elem_this_blk = len(elem_blk_els)
            self.exofile.put_elem_block(elem_blk_id, elem_type, num_elem_this_blk,
                                        num_nodes_per_elem, num_attr)

            # write element connectivity for each element block
            blk_conn = conn[elem_blk_els][:, :num_nodes_per_elem]
            self.exofile.put_elem_conn(elem_blk_id, blk_conn)
            continue

        # write node sets
        for (node_set_id, node_set_nodes) in node_sets:
            num_nodes_in_set = len(node_set_nodes)
            # no distribution factors
            num_dist_fact = 0
            self.exofile.put_node_set_param(node_set_id,
                                            num_nodes_in_set, num_dist_fact)
            self.exofile.put_node_set(node_set_id, node_set_nodes)
            continue

        # write side sets
        for (side_set_id, side_set_elems, side_set_sides) in side_sets:
            num_dist_fact = 0
            num_sides_in_set = len(side_set_elems)
            self.exofile.put_side_set_param(side_set_id, num_sides_in_set,
                                            num_dist_fact)
            self.exofile.put_side_set(side_set_id, side_set_elems, side_set_sides)
            continue

        # write QA records
        now = datetime.datetime.now()
        day = now.strftime("%m/%d/%y")
        hour = now.strftime("%H:%M:%S")
        num_qa_rec = 1
        qa_title = "FEM finite element simulation"
        runid = os.path.splitext(os.path.basename(self.filename))[0]
        qa_record = np.array([[qa_title, runid, day, hour]])
        self.exofile.put_qa(num_qa_rec, qa_record)

        # write results variables parameters and names
        glob_var_names = ["Dtime"]
        self.num_glob_vars = len(glob_var_names)
        self.exofile.put_var_param("g", self.num_glob_vars)
        self.exofile.put_var_names("g", self.num_glob_vars, glob_var_names)

        nod_var_names = np.array([s + "%s" %(x) for x in "xyz"[:num_dim]])
        self.num_nod_vars = len(node_data[0])
        self.exofile.put_var_param("n", self.num_nod_vars)
        self.exofile.put_var_names("n", self.num_nod_vars, node_data[0])

        self.num_elem_vars = len(ele_var_names)
        self.exofile.put_var_param("e", self.num_elem_vars)
        self.exofile.put_var_names("e", self.num_elem_vars, ele_var_names)

        # write element variable truth table
        truth_tab = np.empty((self.num_elem_blk, self.num_elem_vars), dtype=np.int)
        for i in range(self.num_elem_blk):
            for j in range(self.num_elem_vars):
                truth_tab[i, j] = 1
        self.exofile.put_elem_var_tab(self.num_elem_blk, self.num_elem_vars,
                                      truth_tab)

        # write first step
        time_val = 0.
        self.count = 0
        self.exofile.put_time(self.count, time_val)

        # global values
        glob_var_vals = np.zeros(self.num_glob_vars, dtype=np.float64)
        self.exofile.put_glob_vars(self.count, self.num_glob_vars,
                                   glob_var_vals)

        # nodal values
        for k in range(self.num_nod_vars):
            self.exofile.put_nodal_var(self.count, k, self.num_nodes,
                                       node_data[1][:,k])
            continue

        # element values
        for (elem_blk_id, num_elem_this_blk, elem_blk_data) in all_element_data:
            for k in range(self.num_elem_vars):
                self.exofile.put_elem_var(
                    self.count, k, elem_blk_id,
                    num_elem_this_blk, elem_blk_data.T[k])
            continue

        self.exofile.update()
        self.count += 1
        pass

    def finish(self):
        # udpate and close the file
        self.exofile.update()
        self.exofile.close()
        return

    def snapshot(self, ave, node_data, time, dtime):
        """Dump information from current time step to results file

        Parameters
        ----------
        time : float
            Current time

        dt : float
            Time step

        u : array_like
            Nodal displacements

        """
        # write time value
        self.exofile.put_time(self.count, time)

        # write global variables
        glob_var_vals = np.zeros(self.num_glob_vars)
        for j in range(self.num_glob_vars):
            glob_var_vals[j] = dtime
            continue
        self.exofile.put_glob_vars(self.count, self.num_glob_vars, glob_var_vals)

        # write nodal variables
        for k in range(self.num_nod_vars):
            self.exofile.put_nodal_var(self.count, k, self.num_nodes,
                                       node_data[:, k])

        # write element variables
        for (i, ebid) in enumerate(self.elem_blk_ids):
            data = ave[i]
            neeb = data.shape[0]
            for k in range(self.num_elem_vars):
                self.exofile.put_elem_var(self.count, k, ebid, neeb, data[:, k])

        # udpate and close the file
        self.count += 1
        self.exofile.update()

        return

def put_nodal_solution(filename, num_dim, coords, conn, elem_type, u, d=None):

    # create new file
    exofile = ExoFile(filename, mode="w", d=d)

    # initialize file with parameters
    num_nodes = coords.shape[0]
    num_elem = conn.shape[0]
    num_elem_blk = 1
    num_node_sets = 0
    num_side_sets = 0
    title = os.path.splitext(os.path.basename(filename))[0]

    exofile.put_init(title, num_dim, num_nodes, num_elem,
                     num_elem_blk, num_node_sets, num_side_sets)

    # write nodal coordinates values and names to database
    s = "Coord"
    coord_names = np.array([s + "%s" %(x) for x in "xyz"[:num_dim]])
    exofile.put_coord_names(coord_names)
    z = np.zeros(num_nodes) if num_dim <= 2 else coords[:, 2]
    exofile.put_coord(coords[:, 0], coords[:, 1], z)

    # write element order map
    elem_num_map = np.arange(num_elem) + 1
    exofile.put_elem_num_map(elem_num_map)

    # write element block parameters
    elem_blk_id = 1
    elem_blk_els = elem_num_map
    num_nodes_per_elem = conn.shape[1]

    # for now, we do not use attributes
    num_attr = 0
    num_elem_this_blk = len(elem_blk_els)
    exofile.put_elem_block(elem_blk_id, elem_type, num_elem_this_blk,
                           num_nodes_per_elem, num_attr)

    # write element connectivity for each element block
    exofile.put_elem_conn(elem_blk_id, conn)

    # write results variables parameters and names
    glob_var_names = ["Dtime"]
    num_glob_vars = 1
    exofile.put_var_param("g", num_glob_vars)
    exofile.put_var_names("g", num_glob_vars, glob_var_names)

    s = "Displacement"
    nod_var_names = np.array([s + "%s" %(x) for x in "xyz"[:num_dim]])
    num_nod_vars = len(nod_var_names)
    exofile.put_var_param("n", num_nod_vars)
    exofile.put_var_names("n", num_nod_vars, nod_var_names)

    count = 1
    exofile.put_time(count, 1.)
    exofile.put_glob_vars(count, num_glob_vars, np.array([1.]))

    # write nodal variables
    for k in range(num_nod_vars):
        exofile.put_nodal_var(count, k, num_nodes, u[:, k])

    exofile.update()
    exofile.close()
