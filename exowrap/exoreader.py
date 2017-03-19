import os
import sys
import imp
import numpy as np

# Import platform dependent exolib
from _exoconst import *
try:
    import pyexodusii as exolib
except ImportError as e:
    # By this point, the library exists, we just couldn't import it. Check
    # known reasons.
    import re
    if re.search(r"libnetcdf.*", e.message):
        raise ImportError("Set LD_LIBRARY_PATH={0} to load netcdf shared "
                          "object files".format(prefix + "/lib"))
    raise


huge = 1.e99


class ExodusReaderError(Exception):
    pass


class ExodusIIReader(object):

    def __init__(self, exoid, version, f, title, num_dim, num_nodes, num_elem,
                 num_elem_blk, num_node_sets, num_side_sets):
        """Instantiate the ExodusIIReader object

        Parameters
        ----------
        exoid : int
            File ID as returned by one of the factory initialization methods

        num_dim : int
            Number of spatial dimensions [1, 2, 3]

        num_nodes : int
            Number of nodes

        num_elem : int
            Number of elements

        num_elem_blk : int
            Number of element blocks

        num_node_sets : int
            Number of node sets

        num_side_sets : int
            Number of side sets

        Notes
        -----
        The ExodusRead class is an interface to the Exodus II fortran
        bindings. Its methods are named after the analogous method from the
        Exodus II C bindings, minus the prefix 'ex_'.

        The ExodusRead instance returns all arrays as row major (Python
        convention), by transposing arrays passed from the Fortran procedures.

        """
        self.file = f
        self.exoid = exoid
        self.version = version
        self.title = title
        self.num_dim = num_dim
        self.num_nodes = num_nodes
        self.num_elem = num_elem
        self.num_elem_blk = num_elem_blk
        self.num_node_sets = num_node_sets
        self.num_side_sets = num_side_sets

        # Zero based indexing is used throught, but Exodus uses 1 based.
        self._o = 1

        # read coordinates and names
        self.XYZ = np.column_stack(self._get_coord())
        self.coord_names = self._get_coord_names()

        # read element order map
        self.opt_elem_map = self._get_map()
        self.elem_num_map = self._get_elem_num_map()

        # read element block parameters
        self.elem_blk_ids = self._get_elem_blk_ids()
        self.elem_blk_params = self._get_elem_block_params()
        self.elem_blk_props = self._get_elem_block_props()

        # read element connectivity
        self.connect = self._get_elem_conn()

        # read element block attributes
        self.attrib = self._get_elem_attr()

        # read node sets
        self.node_set_ids = self._get_node_set_ids()
        self.node_set_params = self._get_node_set_params()
        self.node_set_props = self._get_node_set_props()

        # read side sets
        self.side_set_ids = self._get_side_set_ids()
        self.side_set_params = self._get_side_set_params()
        self.side_set_props = self._get_side_set_props()

        # tjf_todo: skipped some in ExodussII doc

        # read {global,nodal,element} variables parameters and names
        self._var_names, self._var_indices = self._get_all_var_names()

        # read element variable truth table
        self.elem_var_tab = self._get_elem_var_tab()

        # determine how many time steps are stored
        self.num_time_steps = self._get_number_of_time_steps()

        pass

    @classmethod
    def new_from_exofile(cls, f):
        """Creates a new EXODUS II file instance from another

        Parameters
        ----------
        f : str
            Path to existing exodusII file

        Returns
        -------
        ExodusIIReader : object
            ExodusIIReader instance

        """
        cpu_ws = np.array([0])
        io_ws = np.array([0])
        exoid, vers, ierr = exolib.py_exopen(f, EX_READ, cpu_ws, io_ws)
        if ierr:
            raise ExodusReaderError("Error opening {0}".format(f))
        (title, num_dim, num_nodes, num_elem, num_elem_blk,
         num_node_sets, num_side_sets, ier) = cls._get_init(exoid)

        return cls(exoid, vers, f, title, num_dim, num_nodes, num_elem,
                   num_elem_blk, num_node_sets, num_side_sets)

    def close(self):
        """Close the exodus file

        """
        return exolib.py_exclos(self.exoid)

    def inquire(self, req_info):
        """Inquire values of certain data entities in an EXODUS II file

        Parameters
        ----------
        req_info : int
            A flag which designates what information is requested. It must be
            one of the following constants (predefined in the file
            exodusII.h):

        Returns
        -------
        ret_int : int
            Returned integer, if an integer value is requested (according to
            req_info)

        ret_float : float
            Returned float, if a float value is requested (according to
            req_info);

        ret_char : str
            Returned single character, if a character value is requested
            (according to req_info)

        """
        i, f, s, ierr = exolib.py_exinq(self.exoid, req_info)
        if ierr:
            raise ExodusReaderError("Error inquiring for {0}".format(req_info))
        return i, f, s

    def summary(self):
        """return a summary string

        """
        S = ["Summary", "=" * 80]
        S.append("Exodus file name: {0}".format(self.file))
        S.append("Title: {0}".format(self.title))
        S.append("Number of dimensions: {0}".format(self.num_dim))
        S.append("Coordinate names: {0}".format(" ".join(self.coord_names)))

        S.append("Number of nodes: {0}".format(self.num_nodes))
        S.append("Number of node sets: {0}, Ids={1}".format(
                self.num_node_sets,
                " ".join("{0}".format(x) for x in self.node_set_ids)))

        S.append("Number of elements: {0}".format(self.num_elem))
        S.append("Number of element blocks: {0} Ids={1}".format(
                self.num_elem_blk,
                " ".join("{0}".format(x) for x in self.elem_blk_ids)))

        S.append("Number of side sets: {0}".format(self.num_side_sets))

        for key, name in EX_VAR_TYPES.items():
            keys = self._var_names[key]
            if keys is None:
                keys = []
            S.append("{0} vars: {1}".format(name.title(), len(keys)))
            if keys:
                keys = sorted(keys, key=lambda x: self._var_indices[key][x.upper()])
                n = len(str(len(keys)))
                S.extend(["    {0:>{1}d} {2}".format(i, n, k)
                          for (i, k) in enumerate(keys)])

        S.append("Number of time steps: {0}".format(self.num_time_steps))
        for i in range(self.num_time_steps):
            S.append("    {0} {1}".format(i, self.get_time(i)))

        return "\n".join(S)

    # ----------------------------------- Exodus II API 'get_ex' Methods ---- #
    def get_info(self):
        """Reads information records from the database. The records are
        MAX_LINE_LENGTH-character strings. Memory must be allocated for the
        information records before this call is made. The number of records
        can be determined by invoking inquire

        Returns
        -------
        info : array of strings
            information stored to exodus database

        """
        ninfo, f, c = self.inquire(EX_INQ_INFO)
        info, ierr = exolib.py_exginf(self.exoid, ninfo)
        if ierr:
            raise ExodusReaderError("Error getting information")
        return self.convert_fortran_chararray_to_python(info)

    def get_coord(self, comp=None):
        """Return the coordinates of the nodes

        Parameters
        ----------
        comp : [int, string]
            Component to return
            One of (0, 1, 2) or (x, y, z)

        Returns
        -------
        x, y, z : array_like, (nnode,)
            x, y, z coordinates

        """
        if comp is None:
            return (self.XYZ[:, PY_X_COMP],
                    self.XYZ[:, PY_Y_COMP],
                    self.XYZ[:, PY_Z_COMP])
        try:
            i = {"X": PY_X_COMP, "Y": PY_Y_COMP, "Z": PY_Z_COMP}[comp.upper()]
        except AttributeError:
            # must have been an integer
            i = comp
        except KeyError:
            raise ExodusReaderError("{0}: invalid coordinate "
                                    "component".format(comp))
        return self.XYZ[:, i]

    def get_coords(self):
        """Return the coordinates of the nodes as a single array

        Returns
        -------
        xyz : array_like, (nnode, 3)
            x, y, z coordinates

        """
        return self.XYZ

    def get_coord_names(self):
        """Returns the names of the coordinate arrays

        Returns
        -------
        coord_names : array_like
            Array containing num_dim names (of length MAX_STR_LENGTH) of the
            nodal coordinate arrays.

        """
        return self.coord_names

    def get_elem_var_tab(self):
        """Returns the EXODUS II element variable truth table

        Returns
        -------
        elem_var_tab : ndarray (num_elem_blk, num_elem_var)
            Array containing the element variable truth table.

        """
        return self.elem_var_tab

    def get_elem_blk_ids(self):
        """Returns the IDs of all of the element blocks

        Returns
        -------
        elem_blk_ids : ndarray
            Array of the element blocks IDs. The order of the IDs in this
            array reflects the sequence that the element blocks were
            introduced into the file.

        """
        return self.elem_blk_ids

    def get_map(self):
        """Returns the element map attribute

        Returns
        -------
        elem_map : array_like
            The element map

        """
        return self.elem_map

    def get_elem_num_map(self):
        """Returns the element number map attribute

        Returns
        -------
        elem_map : array_like
            The element number map

        """
        return self.elem_num_map

    def get_elem_block(self, elem_blk_id):
        """Returns parameters used to describe an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID.

        Returns
        -------
        elem_type : str
            The type of elements in the element block.

        num_elem_this_blk : int
            The number of elements in the element block.

        num_nodes_per_elem : int
            Number of nodes per element in the element block

        num_attr : int
            The number of attributes per element in the element block.

        """
        elem_blk_params = self.elem_blk_params.get(elem_blk_id)
        if elem_blk_params is None:
            raise ExodusReaderError("{0}: invalid element block "
                                    "ID".format(elem_blk_id))
        return (elem_blk_params["ELEMENT TYPE"],
                elem_blk_params["NUMBER OF ELEMENTS"],
                elem_blk_params["NUMBER OF NODES PER ELEMENT"],
                elem_blk_params["NUMBER OF ATTRIBUTES"])

    def get_elem_conn(self, elem_blk_id):
        """reads the connectivity array for an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        Returns
        -------
        connect : ndarray, (num_elem_this_blk, num_nodes_per_elem)
            Connectivity array; a list of nodes (internal node IDs; see Node
            Number Map) that define each element. The element index cycles faster
            than the node index.

        """
        elem_blk_idx = self._index(self.elem_blk_ids, elem_blk_id)
        if elem_blk_idx is None:
            raise ExodusReaderError("{0}: not a valid element block "
                                    "ID".format(elem_blk_id))
        return self.connect[elem_blk_idx]

    def get_elem_attr(self, elem_blk_id):
        """Returns the attributes for an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        Returns
        -------
        attrib : list, (num_elem_this_blk, num_attr)
            Dict of (num_attr * num_elem_this_blk) attributes for each element
            block, with the num_attr index cycling faster.

        """
        return self.attrib.get(elem_blk_id)

    def get_node_set_ids(self):
        """Returns the IDs of all of the node sets

        Returns
        -------
        node_set_ids : ndarray, (num_node_sets,)
            List of node set IDs

        """
        return self.node_set_ids

    def get_node_set_param(self, node_set_id):
        """Returns the number of nodes which describe a single node set and
        the number of distribution factors for the node set.

        Paramters
        ---------
        node_set_id : int
            The node set ID

        Returns
        -------
        num_nodes_in_set : int
            The number of nodes in the set

        num_dist_in_set : int
            The number of distribution factors in the set

        """
        node_set_param = self.node_set_params.get(node_set_id)
        if node_set_param is None:
            raise ExodusReaderError("{0}: invalid node set ID".format(node_set_id))
        return (node_set_param["NUMBER OF NODES"],
                node_set_param["NUMBER OF DISTRIBUTION FACTORS"])

    def get_var_param(self, c):
        """Returns the number of global, nodal, nodeset, sideset, or element
        variables stored in the database

        Parameters
        ----------
        c : string
            var type.  one of:
              g for global variable
              n for nodal variable
              e for element variable
              m for nodeset variable
              s for sideset variable

        Returns
        -------
        num_var_param : int
            Number of parameters for the variable

        """
        c = c.upper()
        try:
            names = self._var_names[c]
        except KeyError:
            raise ExodusReaderError("{0}: unrecognized variable type".format(c))
        if names is None:
            return 0
        return len(names)

    def get_var_names(self, c):
        """Reads the names of the results variables from the database

        Parameters
        ----------
        c : string
            var type.  one of:
              g for global variable
              n for nodal variable
              e for element variable
              m for nodeset variable
              s for sideset variable

        Returns
        -------
        names : list
            List of names

        """
        c = c.upper()
        names = self._var_names.get(c)
        if c is None:
            raise ExodusReaderError("{0}: invalid variable type".format(c))
        return names

    def get_time(self, step):
        """reads the time value for a specified time step

        Parameters
        ----------
        step : int
            Time step, 0 based indexing

        Returns
        -------
        time : float
            Time at time step

        """
        istep = self._adjust_step(step)
        time, ierr = exolib.py_exgtim(self.exoid, istep)
        if ierr:
            raise ExodusReaderError("Error getting time at step {0}".format(step))
        return float(time)

    def get_all_times(self):
        """Reads the time values for all time steps

        Returns
        -------
        times : ndarray
            Array of times for all time steps

        """
        times, ierr = exolib.py_exgatm(self.exoid, self.num_time_steps)
        if ierr:
            raise ExodusReaderError("Error getting all times")
        return times

    def get_glob_vars(self, step, disp=0):
        """Read all global variables at one time step

        Parameters
        ----------
        step : int
            Time step, 0 based indexing

        disp : int, optional
            If disp > 0, return dictionary of {glob_var: glob_var_val}

        Returns
        -------
        var_values : ndarray, (num_glob_vars,)
            Global variable values for the stepth time step

        """
        istep = self._adjust_step(step)
        num_glo_vars = len(self._var_names[PY_GLOBAL])
        var_values, ierr = exolib.py_exggv(self.exoid, istep, num_glo_vars)
        if ierr:
            raise ExodusReaderError("Error getting global variables at "
                                    "step {0}".format(step))
        if not disp:
            return var_values
        return dict(zip(self._var_names[PY_GLOBAL], var_values))

    def get_glob_var_time(self, glob_var, beg_time_step=0, end_time_step=-1):
        """Read global variable through time

        glob_var : str
            The desired global variable

        beg_time_step : int
            The beginning time step for which a nodal variable value is
            desired. This is not a time value but rather a time step number,
            as described under ex_put_time.

        end_time_step : int
            The last time step for which a nodal variable value is desired. If
            negative, the last time step in the database will be used.

        Returns
        -------
        var_values : ndarray
            Array of (end_time_step - beg_time_step + 1) values of the
            global variable

        """
        var_index = self._var_index(PY_GLOBAL, glob_var)
        istpb = self._adjust_step(beg_time_step)
        istpe = self._adjust_step(end_time_step)
        var_values, ierr = exolib.py_exggvt(self.exoid, var_index, istpb, istpe)
        if ierr:
            raise ExodusReaderError("Error getting global "
                                    "variable {0}".format(glob_var))
        return var_values

    def get_nodal_var(self, step, nodal_var):
        """Read nodal variable at one time step

        Parameters
        ----------
        step : int
            The time step, 0 indexing

        nodal_var : str
            The nodal variable

        Returns
        -------
        var_values : ndarray
            num_nodes values of the nodal_var_indexth nodal variable for the
            stepth time step.

        """
        istep = self._adjust_step(step)
        var_index = self._var_index(PY_NODAL, nodal_var)
        var_values, ierr = exolib.py_exgnv(
            self.exoid, istep, var_index, self.num_nodes)
        if ierr:
            raise ExodusReaderError("Error getting nodal variable {0} at "
                                    "step {1}".format(nodal_var, step))
        return var_values

    def get_nodal_var_time(self, nodal_var, node_num, beg_time_step=0,
                           end_time_step=-1):
        """Reads the values of a nodal variable for a single node through a
        specified number of time steps

        Parameters
        ----------
        nodal_var : str
            The desired nodal variable

        node_num : int
            The internal ID (see Node Number Map) of the desired node

        beg_time_step : int
            The beginning time step for which a nodal variable value is
            desired. This is not a time value but rather a time step number,
            as described under ex_put_time.

        end_time_step : int
            The last time step for which a nodal variable value is desired. If
            negative, the last time step in the database will be used.

        Returns
        -------
        var_vals : ndarray
            Array of (end_time_step - beg_time_step + 1) values of the
            node_numberth node for the nodal_var_indexth nodal variable.

        """
        var_index = self._var_index(PY_NODAL, nodal_var)
        istpb = self._adjust_step(beg_time_step)
        istpe = self._adjust_step(end_time_step)
        var_values, ierr = exolib.py_exgnvt(
            self.exoid, var_index, node_num + self._o, istpb, istpe)
        if ierr:
            raise ExodusReaderError("Error getting nodal "
                                    "variable {0}".format(nodal_var))
        return var_values

    def get_elem_var(self, step, elem_var, elem_blk_ids=None):
        """Read element variable at one time step

        Parameters
        ----------
        step : int
            The time step, 0 indexing

        elem_var : str
            The element variable

        elem_blk_ids : list, optional
            If given, list of element block IDs

        Returns
        -------
        elem_var : list

        """

        # Get the element block[s]
        if elem_blk_ids is None:
            elem_blk_ids = [x for x in self.elem_blk_ids]
        if not isinstance(elem_blk_ids, (list, tuple)):
            elem_blk_ids = [elem_blk_ids]

        istep = self._adjust_step(step)
        var_index = self._var_index(PY_ELEMENT, elem_var)

        elem_var = []
        for i in range(self.num_elem_blk):
            elem_blk_id = self.elem_blk_ids[i]
            if elem_blk_id not in elem_blk_ids:
                continue
            netb = self.elem_blk_params[elem_blk_id]["NUMBER OF ELEMENTS"]
            var_values, ierr = exolib.py_exgev(
                self.exoid, istep, var_index, elem_blk_id, netb)
            if ierr:
                raise ExodusReaderError("Error getting element variable {0} "
                                        "at step {1}".format(elem_var, step))
            elem_var.append(var_values)
        return elem_var

    def get_elem_var_time(self, elem_var, elem_num, beg_time_step=0,
                          end_time_step=-1):
        """Read element variable through time

        Parameters
        ----------
        elem_var : str
            The desired element variable

        elem_num : int
            The internal ID (see Element Number Map) of the desired element

        beg_time_step : int
            The beginning time step for which a nodal variable value is
            desired. This is not a time value but rather a time step number,
            as described under ex_put_time.

        end_time_step : int
            The last time step for which a nodal variable value is desired. If
            negative, the last time step in the database will be used.

        Returns
        -------
        var_vals : ndarray
            Array of (end_time_step - beg_time_step + 1) values of the
            node_numberth node for the nodal_var_indexth nodal variable.

        """
        var_index = self._var_index(PY_ELEMENT, elem_var)
        istpb = self._adjust_step(beg_time_step)
        istpe = self._adjust_step(end_time_step)
        var_values, ierr = exolib.py_exgevt(
            self.exoid, var_index, elem_num + self._o, istpb, istpe)
        if ierr:
            raise ExodusReaderError("Error getting element "
                                    "variable {0}".format(elem_var))
        return var_values

    # --------------------------------------------------- Private Methods --- #
    # The private methods below are called at instantiation and store the
    # information retrieved from the database as class attributes. Companion
    # methods of the same name, without the prepended "_", simply return the
    # appropriate values without going in to the database again.
    def _get_coord(self):
        """Read the coordinates of the nodes

        Returns
        -------
        x, y, z : array_like
            x, y, z coordinates

        """
        x, y, z, ierr = exolib.py_exgcor(self.exoid, self.num_nodes)
        if ierr:
            raise ExodusReaderError("Error getting nodal coordinates")
        return x, y, z

    def _get_coord_names(self):
        """Reads the names of the coordinate arrays from the database.

        Returns
        -------
        coord_names : array_like
            Array containing num_dim names (of length MAX_STR_LENGTH) of the
            nodal coordinate arrays.

        """
        coord_names, ierr = exolib.py_exgcon(self.exoid, self.num_dim)
        if ierr:
            raise ExodusReaderError("Error getting coordinate names")
        return self.convert_fortran_chararray_to_python(coord_names)

    def _get_elem_blk_ids(self):
        """Reads the IDs of all of the element blocks from the database

        Returns
        -------
        elem_blk_ids : ndarray
            Array of the element blocks IDs. The order of the IDs in this
            array reflects the sequence that the element blocks were
            introduced into the file.

        """
        elem_blk_ids, ierr = exolib.py_exgebi(self.exoid, self.num_elem_blk)
        if ierr:
            raise ExodusReaderError("Error getting element block IDs")
        return elem_blk_ids

    def _get_map(self):
        """Reads the optimized element order map from the database

        Returns
        -------
        elem_map : array_like
            The element map

        """
        elem_map, ierr = exolib.py_exgmap(self.exoid, self.num_elem)
        if ierr:
            raise ExodusReaderError("Error getting element map")
        return elem_map - self._o

    def _get_elem_num_map(self):
        """Reads the element number map from the database

        Returns
        -------
        elem_map : array_like
            The element map

        """
        elem_num_map, ierr = exolib.py_exgenm(self.exoid, self.num_elem)
        if ierr:
            raise ExodusReaderError("Error getting element number map")
        return elem_num_map - self._o

    def _get_elem_block_params(self):
        elem_block_params = {}
        for elem_blk_id in self.elem_blk_ids:
            (et, neb, nn, na) = self._get_elem_block(elem_blk_id)
            elem_block_params[elem_blk_id] = {
                "ELEMENT TYPE": et,
                "NUMBER OF ELEMENTS": neb,
                "NUMBER OF NODES PER ELEMENT": nn,
                "NUMBER OF ATTRIBUTES": na}
            continue
        return elem_block_params

    def _get_elem_block_props(self):
        num_props, f, c = self.inquire(EX_INQ_EB_PROP)
        prop_names = self._get_prop_names(EX_ELEM_BLOCK, num_props)
        elem_block_props = {}
        for i in range(num_props):
            prop_values = np.empty(self.num_elem_blk, dtype=np.int)
            for j in range(self.num_elem_blk):
                prop_values[j], ierr = exolib.py_exgp(
                    self.exoid, EX_ELEM_BLOCK, self.elem_blk_ids[j], prop_names[i])
            elem_block_props[prop_names[i]] = prop_values
        return elem_block_props

    def _get_elem_conn(self):
        """Reads the connectivity array for all element blocks from the database

        Returns
        -------
        connect : ndarray, (num_elem_this_blk, num_nodes_per_elem)
            Connectivity array; a list of nodes (internal node IDs; see Node
            Number Map) that define each element. The element index cycles faster
            than the node index.

        """
        connect = []
        for i, eid in enumerate(self.elem_blk_ids):
            nnte = self.elem_blk_params[eid]["NUMBER OF NODES PER ELEMENT"]
            netb = self.elem_blk_params[eid]["NUMBER OF ELEMENTS"]
            conn, ierr = exolib.py_exgelc(self.exoid, eid, nnte, netb)
            if ierr:
                raise ExodusReaderError("Error getting element connectivity")
            connect.append(np.reshape(conn, (netb, nnte)))
        return connect

    def _get_elem_attr(self):
        """Reads the attributes for all element blocks in database

        Returns
        -------
        attrib : dict, {elem_blk_id: (num_elem_this_blk, num_attr)}
            Dict of (num_attr * num_elem_this_blk) attributes for each element
            block, with the num_attr index cycling faster.

        """
        attrib = {}
        for eid in self.elem_blk_ids:
            num_attr = self.elem_blk_params[eid]["NUMBER OF ATTRIBUTES"]
            if not num_attr:
                continue
            elem_attr, ierr = exolib.py_exgeat(self.exoid, eid, num_attr)
            if ierr:
                raise ExodusReaderError("Error getting element attribute")
            attrib[eid] = elem_attr
        return attrib

    def _get_node_set_ids(self):
        """Reads the IDs of all of the node sets from the database

        Returns
        -------
        node_set_ids : ndarray, (num_node_sets,)
            List of node set IDs

        """
        if not self.num_node_sets:
            return np.empty(0)
        node_set_ids, ierr = exolib.py_exgnsi(self.exoid, self.num_node_sets)
        if ierr:
            raise ExodusReaderError("Error getting node set IDs")
        return node_set_ids

    def _get_node_set_params(self):
        """Reads the node set parameters for each node set

        Returns
        -------
        node_set_params : dict
            A dictionary containing node set parameters with the following keys
            NUMBER OF NODES, NODE LIST,
            NUMBER OF DISTRIBUTION FACTORS
            DISTRIBUTION FACTORS

        """
        node_set_params = {}
        num_nodes_in_set = np.empty(self.num_node_sets, dtype=np.int)
        num_df_in_set = np.empty(self.num_node_sets, dtype=np.int)
        dist_fact = None

        for i in range(self.num_node_sets):
            (num_nodes_in_set[i], num_df_in_set[i],
             ierr) = exolib.py_exgnp(self.exoid, self.node_set_ids[i])
            if ierr:
                raise ExodusReaderError("Error getting node set params")

        for i in range(self.num_node_sets):
            node_list, ierr = exolib.py_exgns(
                self.exoid, self.node_set_ids[i], num_nodes_in_set[i])

            if num_df_in_set[i] > 0:
                dist_fact, ierr = exolib.py_exgnsd(
                    self.exoid, self.node_set_ids[i], num_df_in_set[i])

            node_set_params[self.node_set_ids[i]] = {
                    "NUMBER OF NODES": num_nodes_in_set[i],
                    "NODE LIST": node_list - self._o,
                    "NUMBER OF DISTRIBUTION FACTORS": num_df_in_set[i],
                    "DISTRIBUTION FACTORS": dist_fact}

        return node_set_params

    def _get_node_set_props(self):
        """Read node set properties from the database

        Returns
        -------
        node_set_props : dict, {prop_name: prop_values}
            The node set properties for each node set

        Notes
        -----
        Number of properties and property names are read from the database,
        afterwhich the values of the properties are read and put in the
        node_set_props dictionary.

        """
        num_props, f, c = self.inquire(EX_INQ_NS_PROP)
        prop_names = self._get_prop_names(EX_NODE_SET, num_props)
        node_set_props = {}
        for i in range(num_props):
            prop_values = np.empty(self.num_node_sets, dtype=np.int)
            for j in range(self.num_node_sets):
                prop_values[j], ierr = exolib.py_exgp(
                    self.exoid, EX_NODE_SET, self.node_set_ids[j], prop_names[i])
            node_set_props[prop_names[i]] = prop_values
        return node_set_props

    def _get_side_set_ids(self):
        """Reads the IDs of all of the side sets from the database

        Returns
        -------
        side_set_ids : ndarray
            The side set IDs

        """
        if not self.num_side_sets:
            return []
        side_set_ids, ierr = exolib.py_exgssi(self.exoid, self.num_side_sets)
        if ierr:
            raise ExodusReaderError("Error getting side set IDs")
        return side_set_ids

    def _get_side_set_params(self):
        """Reads the side set parameters for each node set

        Returns
        -------
        side_set_params : dict
            A dictionary containing side set parameters with the following keys
            ELEMENTS
            SIDES
            SIDE NODE COUNT
            NODES
            DISTRIBUTION FACTORS

        """

        side_set_params = {}

        num_sides_in_set = np.empty(self.num_side_sets, dtype=np.int)
        num_df_in_set = np.empty(self.num_side_sets, dtype=np.int)

        # get the sideset params for each side
        for i in range(self.num_side_sets):
            (num_sides_in_set[i], num_df_in_set[i],
             ierr) = exolib.py_exgsp(self.exoid, self.side_set_ids[i])
            if ierr:
                raise ExodusReaderError("Error getting side set params")

        for i in range(self.num_side_sets):

            elem_list, side_list, ierr = exolib.py_exgss(
                self.exoid, self.side_set_ids[i], num_sides_in_set[i])

            # get side set node list to correlate to dist factors
            node_ctr_list, node_list, dist_fact = None, None, None
            if num_df_in_set[i] > 0:
                num_elem_in_set = num_sides_in_set[i]
                node_ctr_list, node_list, ierr = exolib.py_exgssn(
                    self.exoid, self.side_set_ids[i], num_elem_in_set,
                    num_df_in_set[i])
                dist_fact, ierr = exolib.py_exgssd(
                    self.exoid, self.side_set_ids[i], num_df_in_set[i])

            side_set_params[self.side_set_ids[i]] = {
                "ELEMENTS": elem_list - self._o,
                "SIDES": side_list,
                "SIDE NODE COUNT": node_ctr_list,
                "NODES": None if node_list is None else node_list - self._o,
                "DISTRIBUTION FACTORS": dist_fact}

            continue

        return side_set_params

    def _get_side_set_props(self):
        """Read side set properties from the database

        Returns
        -------
        side_set_props : dict, {prop_name: prop_values}
            The side set properties for each node set

        Notes
        -----
        Number of properties and property names are read from the database,
        afterwhich the values of the properties are read and put in the
        node_set_props dictionary.

        """
        num_props, f, c = self.inquire(EX_INQ_SS_PROP)
        prop_names = self._get_prop_names(EX_SIDE_SET, num_props)
        side_set_props = {}
        for i in range(num_props):
            prop_values = np.empty(self.num_side_sets, dtype=np.int)
            for j in range(self.num_side_sets):
                prop_values[j], ierr = exolib.py_exgp(
                    self.exoid, EX_SIDE_SET, self.side_set_ids[j], prop_names[i])
            side_set_props[prop_names[i]] = prop_values
        return side_set_props

    def _get_all_var_names(self):
        """Reads the number of global, nodal, nodeset, sideset, or element
        variables stored and the names of the results variables from the
        database

        """
        var_names, var_indices = {}, {}
        for key in EX_VAR_TYPES:
            num_vars, ierr = exolib.py_exgvp(self.exoid, key)
            if ierr:
                raise ExodusReaderError("Error getting '{0}' "
                                        "parameters".format(key))
            if num_vars == 0:
                var_names[key] = None
                continue
            names, ierr = exolib.py_exgvan(self.exoid, key, num_vars)
            if ierr:
                raise ExodusReaderError("Error getting '{0}' names".format(key))
            names = self.convert_fortran_chararray_to_python(names)

            # now, create a dictionary of name:index pairs
            indices = dict(zip([x.upper() for x in names], range(num_vars)))

            var_names[key] = names
            var_indices[key] = indices
            continue

        return var_names, var_indices

    def _get_elem_block(self, elem_blk_id):
        """Reads parameters used to describe an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID.

        Returns
        -------
        elem_type : str
            The type of elements in the element block.

        num_elem_this_blk : int
            The number of elements in the element block.

        num_nodes_per_elem : int
            Number of nodes per element in the element block

        num_attr : int
            The number of attributes per element in the element block.

        """
        (elem_type, num_elem_this_blk, num_nodes_per_elem,
         num_attr, ierr) = exolib.py_exgelb(self.exoid, elem_blk_id)
        if ierr:
            raise ExodusReaderError("Error getting element block parameters")
        return (elem_type.strip(), num_elem_this_blk,
                num_nodes_per_elem, num_attr)

    def _get_prop_names(self, obj_type, num_props):
        """Reads names of integer properties stored for an element block, node
        set, or side set

        Parameters
        ----------
        obj_type : int
            Type of object; use one of the following options:
              EX_ELEM_BLOCK To designate an element block.
              EX_NODE_SET   To designate a node set.
              EX_SIDE_SET   To designate a side set.
              EX_ELEM_MAP   To designate an element map.
              EX_NODE_MAP   To designate a node map.

        Returns
        -------
        prop_names : list
            List of property names

        """
        if not num_props:
            return []
        if obj_type not in (EX_ELEM_BLOCK, EX_NODE_SET, EX_SIDE_SET, EX_ELEM_MAP,
                            EX_NODE_MAP):
            raise ExodusReaderError("{0}: unrecognized object type".format(otype))
        prop_names, ierr = exolib.py_exgpn(self.exoid, obj_type, num_props)
        if ierr:
            raise ExodusReaderError("Error getting node set prop names")
        return self.convert_fortran_chararray_to_python(prop_names)

    def _get_number_of_time_steps(self):
        """Read the number of time steps in the database

        Returns
        -------
        nsteps : int
            The number of time steps
        """
        nsteps, fdum, cdum = self.inquire(EX_INQ_TIME)
        return nsteps

    def _get_elem_var_tab(self):
        """Reads the EXODUS II element variable truth table from the database

        Returns
        -------
        elem_var_tab : ndarray (num_elem_blk, num_elem_var)
            Array containing the element variable truth table.

        """
        ele_vars = self._var_names[PY_ELEMENT]
        if ele_vars is None:
            return np.empty((self.num_elem_blk, 0))
        elem_var_tab, ierr = exolib.py_exgvtt(
            self.exoid, self.num_elem_blk, len(ele_vars))
        return elem_var_tab.T

    def _adjust_step(self, step):
        """Adjust the user given step for before diving in to the database

        Parameters
        ----------
        step : int
            The time step, 0 based indexing

        Returns
        -------
        adjusted_step : int
            The adjusted step, 1 based indexing

        Notes
        -----
        If step < 0 or > num_time_steps, adjusted_step = num_time_steps
        Else adjusted_step = step + 1

        """
        step = int(step) + self._o
        if step < self.num_time_steps and step > 0:
            return step
        return self.num_time_steps

    def _var_index(self, c, var):
        """Return the index of the c type variable in the database

        Parameters
        ----------
        c : string
            var type.  one of:
              g for global variable
              n for nodal variable
              e for element variable
              m for nodeset variable
              s for sideset variable

        var : str
            The desired variable

        Returns
        -------
        var_index : int
            1 based index of the variable

        """
        c = c.upper()
        var = var.upper()
        var_index = self._var_indices[c].get(var)
        if var_index is None:
            raise ExodusReaderError("{0}: no such {1} "
                                    "variable".format(var, EX_VAR_TYPES.get(c)))
        return var_index + 1

    def _process_parlist(self):
        """
        """
        assert len(self.parlist) > 0

        self.title = ''
        self.storage_type = self.parlist[0].storage_type
        self.ndim = self.parlist[0].ndim
        for i in range(max_type_index):
            self.num[i] = self.parlist[0].num[i]
        self.num[EX_NODE] = 0
        self.num[EX_EDGE] = 0
        self.num[EX_FACE] = 0
        self.num[EX_ELEM] = 0
        self.idmap = self.parlist[0].idmap

        # need to copy the meta data because the total counts need adjustment
        self.meta = []
        for L in self.parlist[0].meta:
            newL = []
            for L2 in L:
                newL2 = []
                for T in L2:
                    newL2.append(T)  # this references the tuple, which is immutable
                    continue
                newL.append( newL2 )
                continue
            self.meta.append( newL )
            continue

        # block information may not be contained in some of the parallel files;
        # use "NULL" element type as an indicator
        for exof in self.parlist:
            for t in [EX_EDGE_BLOCK, EX_FACE_BLOCK, EX_ELEM_BLOCK]:
                for bid in exof.getIds(t):
                    T = exof.getBlock(t,bid)
                    if T[2] != "" and T[2] != "NULL":
                        self.meta[t][ exof.getIndex(t,bid) ] = T

        self.vars       = self.parlist[0].vars
        self.var_tt     = self.parlist[0].var_tt
        self.qa_records = []
        self.times      = self.parlist[0].times

        # collect unique global ids for each type
        maps = {}
        for t in [EX_NODE, EX_EDGE, EX_FACE, EX_ELEM]:
            maps[t] = {}

        # collect unique global ids for each block id
        blockmaps = {}
        for t in [EX_ELEM_BLOCK, EX_EDGE_BLOCK, EX_FACE_BLOCK]:
            blockmaps[t] = {}
            for bid in self.parlist[0].getIds(t):
                blockmaps[t][bid] = {}

        # collect unique global ids in each set
        setmaps = {}
        setdist = {}
        for t in [EX_NODE_SET,EX_SIDE_SET,EX_EDGE_SET,EX_FACE_SET,EX_ELEM_SET]:
            setmaps[t] = {}
            setdist[t] = {}
            for sid in self.parlist[0].getIds(t):
                setmaps[t][sid] = {}
                setdist[t][sid] = 0

        for exof in self.parlist:

            if len(self.title) < len(exof.title):
                self.title = exof.title

            if exof.storage_type != self.storage_type:
                raise Exception("floating point storage types are not "
                                "consistent across parallel files")

            if exof.ndim != self.ndim:
                raise Exception("spatial dimension is not "
                                "consistent across parallel files")

            for t in [ EX_ELEM_BLOCK, EX_NODE_SET, EX_SIDE_SET, EX_ELEM_MAP,
                       EX_NODE_MAP, EX_EDGE_BLOCK, EX_EDGE_SET, EX_FACE_BLOCK,
                       EX_FACE_SET, EX_ELEM_SET, EX_EDGE_MAP, EX_FACE_MAP,
                       EX_GLOBAL ]:
                if exof.num[t] != self.num[t]:
                    raise Exception("number of {0} are not consistent across "
                                    "parallel files".format(type_map[t]))

                # use the qa records from the file that has the most
                if len(self.qa_records) < len(exof.qa_records):
                    self.qa_records = exof.qa_records

                if len(self.times) != len(exof.times):
                    raise Exception("number of time steps are not consistent "
                                    "across parallel files: {0} != {1}".format(
                                        len(self.times), len(exof.times)))

            # read and store the local to global map for each file
            exof.l2g = {}
            exof.l2g[EX_NODE] = exof.readMap( EX_NODE_MAP, -1 )
            exof.l2g[EX_EDGE] = exof.readMap( EX_EDGE_MAP, -1 )
            exof.l2g[EX_FACE] = exof.readMap( EX_FACE_MAP, -1 )
            exof.l2g[EX_ELEM] = exof.readMap( EX_ELEM_MAP, -1 )

            # accumulate the unique global ids for each type
            for t in [EX_NODE, EX_EDGE, EX_FACE, EX_ELEM]:
                i = 0
                while i < len(exof.l2g[t]):
                    maps[t][ exof.l2g[t][i] ] = None
                    i = i + 1

            # accumulate the unique global ids in each block
            exof.blockoff = {}
            for tb,t in [ (EX_ELEM_BLOCK, EX_ELEM),
                          (EX_EDGE_BLOCK, EX_EDGE),
                          (EX_FACE_BLOCK, EX_FACE) ]:
                exof.blockoff[tb] = {}
                e = 0
                for (bid,cnt,typename,n_per,g_per,f_per,nattr) in exof.meta[tb]:
                    i = 0
                    while i < cnt:
                        blockmaps[tb][bid][ exof.l2g[t][e+i] ] = None
                        i = i + 1
                    exof.blockoff[tb][bid] = e  # the elem offset for each block
                    e = e + cnt

            # accumulate the unique global ids in each set
            for t,to in [ (EX_NODE_SET, EX_NODE),
                          (EX_SIDE_SET, EX_ELEM),
                          (EX_EDGE_SET, EX_EDGE),
                          (EX_FACE_SET, EX_FACE),
                          (EX_ELEM_SET, EX_ELEM) ]:
                for sid in exof.getIds(t):
                    d1,cnt,ndist = exof.getSet(t,sid)
                    if cnt > 0 and ndist > 0:
                        assert ndist % cnt == 0
                        setdist[t][sid] = ndist/cnt
                    set,aux = exof.readSet(t,sid)
                    l2g = exof.l2g[to]
                    n = len(set)
                    i = 0
                    if t in [EX_NODE_SET,EX_ELEM_SET]:
                        while i < n:
                            setmaps[t][sid][ l2g[ set[i] ] ] = None
                            i = i + 1
                    else:
                        while i < n:
                            p = ( l2g[ set[i] ], aux[i] )
                            setmaps[t][sid][ p ] = None
                            i = i + 1

        # these map total local indexes to global numbers
        self.gids = {}
        for t in [EX_NODE, EX_EDGE, EX_FACE, EX_ELEM]:
            self.gids[t] = maps[t].keys()
            self.gids[t].sort()
            self.num[t] = len(self.gids[t])  # also set the total count here
        maps = None

        # compute map from global numbers to total local indexes
        self.g2l = {}
        for t in [EX_NODE, EX_EDGE, EX_FACE, EX_ELEM]:
            self.g2l[t] = {}
            i = 0
            while i < len(self.gids[t]):
                self.g2l[t][ self.gids[t][i] ] = i
                i = i + 1

        # set block counts and store block local index offsets
        self.blockoff = {}
        for tb in [EX_ELEM_BLOCK, EX_EDGE_BLOCK, EX_FACE_BLOCK]:
            self.blockoff[tb] = {}
            off = 0
            for i in range(len(self.meta[tb])):
                T = self.meta[tb][i]
                bid = T[0]
                newcnt = len(blockmaps[tb][bid])
                self.meta[tb][i] = (T[0],newcnt,T[2],T[3],T[4],T[5],T[6])
                self.blockoff[tb][bid] = off
                off = off + newcnt
        blockmaps = None

        # do the set counts and keep a map of set global ids to set indexes
        self.setg2l = {}
        for t in [EX_NODE_SET, EX_SIDE_SET,EX_EDGE_SET,EX_FACE_SET,EX_ELEM_SET]:
            self.setg2l[t] = {}
            for i in range(len(self.meta[t])):
                T = self.meta[t][i]
                sid = T[0]
                newcnt = len(setmaps[t][sid])
                ndist = setdist[t][sid] * newcnt
                self.meta[t][i] = (T[0],newcnt,ndist)
                L = setmaps[t][sid].keys()
                L.sort()
                D = {}
                for i in xrange(len(L)):
                    D[L[i]] = i
                self.setg2l[t][sid] = D
                L = None
        setmaps = None
        setdist = None

        # set map counts
        for t,to in [ (EX_ELEM_MAP, EX_ELEM),
                      (EX_NODE_MAP, EX_NODE),
                      (EX_EDGE_MAP, EX_EDGE),
                      (EX_FACE_MAP, EX_FACE) ]:
            for i in range(len(self.meta[t])):
                T = self.meta[t][i]
                self.meta[t][i] = ( T[0], self.num[to] )

    # ----------------------------------------- Non-Exodus II API Methods ---- #
    def num_els_in_block(self, elem_blk_id):
        """Return the number of elements in a block

        Parameters
        ----------
        elem_blk_id : int
            The block ID

        Returns
        -------
        num_els_in_block : int
            The number of elements in the block with ID elem_blk_id

        """
        return self.get_elem_block(elem_blk_id)[1]

    def nodes_in_node_set(self, node_set_id):
        """Return a list of nodes in the node set

        Parameters
        ----------
        node_set_id : int
            The node set ID

        Returns
        -------
        node_list : ndarray
            Array of node IDs

        """
        # Get only those nodes in the requested IDs
        node_set_params = self.node_set_params.get(node_set_id)
        if node_set_params is None:
            valid = ", ".join(["{0}".format(x)
                               for x in self.node_set_params])
            raise ExodusReaderError("{0}: invalid node set ID.  Valid IDs "
                                    "are: {1}".format(node_set_id, valid))
        return np.array(node_set_params["NODE LIST"])

    def nodes_in_region(self, xlims=(-huge, huge), ylims=(-huge, huge),
                        zlims=(-huge, huge), node_set_ids=None):
        """Return a list of nodes in the region bounded by (xlims, ylims, zlims)

        Parameters
        ----------
        xlims, ylims, zlims : tuple of floats
            Floats defining ([xyz]min, [xyz]max)

        node_set_id : list of ints, optional
            Node set IDs

        Returns
        -------
        node_list : ndarray
            Array of node IDs

        """
        xmin, xmax = xlims
        ymin, ymax = ylims
        zmin, zmax = zlims
        if node_set_ids is None:
            node_list = np.arange(self.num_nodes)
        else:
            # Get only those nodes in the requested IDs
            if not isinstance(node_set_ids, (list, tuple)):
                node_set_ids = [node_set_ids]
            node_lists = [self.nodes_in_node_set(x) for x in node_set_ids]
            node_list = np.array([node for node_list in node_lists
                                  for node in node_list], dtype=np.int)
        return node_list[(self.XYZ[node_list, PY_X_COMP] >= xmin) &
                         (self.XYZ[node_list, PY_X_COMP] <= xmax) &
                         (self.XYZ[node_list, PY_Y_COMP] >= ymin) &
                         (self.XYZ[node_list, PY_Y_COMP] <= ymax) &
                         (self.XYZ[node_list, PY_Z_COMP] >= zmin) &
                         (self.XYZ[node_list, PY_Z_COMP] <= zmax)]

    def elems_in_region(self, xlims=(-huge, huge), ylims=(-huge, huge),
                        zlims=(-huge, huge), node_set_ids=None):
        """Return a list of elements in the region bounded by
        (xlims, ylims, zlims)

        Parameters
        ----------
        xlims, ylims, zlims : tuple of floats
            Floats defining ([xyz]min, [xyz]max)

        node_set_id : list of ints, optional
            Node set IDs

        Returns
        -------
        elem_list : ndarray
            Array of element IDs

        """
        # get the nodes in the bounding box
        node_list = self.nodes_in_region(xlims=xlims, ylims=ylims, zlims=zlims,
                                         node_set_ids=node_set_ids)
        # get elements connected to nodes
        return self.elems_from_nodes(node_list, strict=False)

    def elems_from_nodes(self, node_list, strict=True):
        """Return a list of elements whose nodes are in node_list

        Parameters
        ----------
        node_list : ndarray of ints
            Array of nodes

        strict : bool, optional
            If False, return element if more than half its nodes are in the
            node_list

        Returns
        -------
        elem_list : ndarray
            Array of element IDs

        """
        # loop through each element block, finding elements whose nodes are
        # in node_list.  Convert to global element IDs
        def issubset(a, b):
            """Return True if the set a is a subset of the set b, else False"""
            return a <= b if strict else len(a & b) >= len(a) / 2.

        elem_list, num_elems_seen, node_set = [], 0, set(node_list)
        for i, blk_conn in enumerate(self.connect):
            elem_list.extend([num_elems_seen + i_elem
                              for (i_elem, elem_conn) in enumerate(blk_conn)
                              if issubset(set(elem_conn), node_set)])
            num_elems_seen += blk_conn.shape[0]
        return np.array(elem_list, dtype=np.int)

    def elems_in_blk(self, elem_blk_id):
        """Return a list of elements in block elem_blk_id

        Parameters
        ----------
        elem_blk_id : int
            Element block ID

        Returns
        -------
        elem_list : ndarray
            Array of element IDs in elem_blk_id

        """
        if elem_blk_id not in self.elem_blk_ids:
            raise ExodusReaderError("{0}: invalid elem_blk_id".format(elem_blk_id))
        # connectivity of element block elem_blk_id
        conn_idx = np.where(self.elem_blk_ids == elem_blk_id)[0][0]

        # number of elements in preceding block elem_blk_id
        n = sum(len(x) for x in self.connect[:conn_idx])

        # element IDs for elements in elem_blk_id
        elem_ids = np.array([n + i for i in range(len(self.connect[conn_idx]))])
        elem_ids = elem_ids - self._o

        return self.elem_num_map[elem_ids]

    def var_names(self, var_type):
        var_type = var_type.upper().strip()
        for (ex_var, val) in EX_VAR_TYPES.items():
            if var_type == val: break
        else:
            raise ExodusReaderError("{0}: invalid var_type".format(var_type))
        return self._var_names.get(ex_var, [])

    def glob_var_names(self):
        return self._var_names.get(PY_GLOBAL, [])

    def elem_var_names(self):
        return self._var_names.get(PY_ELEMENT, [])

    def nodal_var_names(self):
        return self._var_names.get(PY_NODAL, [])

    # --------------------------------------------------- Static Methods ---- #
    @staticmethod
    def _get_init(exoid):
        """Gets the initialization parameters from the ExodusII file

        Parameters
        ----------
        exoid : int
            File ID as returned by one of the factory initialization methods

        Returns
        -------
        title : str
            Title

        num_dim : int
            Number of spatial dimensions [1, 2, 3]

        num_nodes : int
            Number of nodes

        num_elem : int
            Number of elements

        num_elem_blk : int
            Number of element blocks

        num_node_sets : int
            Number of node sets

        num_side_sets : int
            Number of side sets

        """
        (title, num_dim, num_nodes, num_elem, num_elem_blk,
         num_node_sets, num_side_sets, ierr) = exolib.py_exgini(exoid)

        if ierr:
            raise ExodusReaderError("Error getting exodus file initial info")

        return (title, num_dim, num_nodes, num_elem, num_elem_blk,
                num_node_sets, num_side_sets, ierr)

    @staticmethod
    def _index(mapping, element):
        """Return the index corresponding of element in mapping

        """
        try: return mapping.index(element)
        except ValueError: return None

    @staticmethod
    def convert_fortran_chararray_to_python(char):
        """Strip and join Fortran character array to a python character array

        Parameters
        ----------
        char : fortran character array

        Returns
        -------
        pychar : list

        """
        pychar = ["".join(x for x in char.T[:, i]).strip()
                  for i in range(char.shape[0])]
        return pychar


if __name__ == "__main__":
    f = "tests/sample.exo"
    exofile = ExodusIIReader.new_from_exofile(f)
    print exofile.summary()
