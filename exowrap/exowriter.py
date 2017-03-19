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

class ExodusIIWriterError(Exception):
    pass


class ExodusIIWriter(object):
    """The ExodusIIWriter class

    """

    def __init__(self, filename, exoid, offset=1):
        """Instantiate the ExodusIIWriter object

        Parameters
        ----------
        exoid : int
            File ID as returned by one of the factory initialization methods

        offset : int {optional, 1}
            Optional offset to be applied to node and element numbering.

        Notes
        -----
        The ExodusIIWriter class is an interface to the Exodus II fortran
        bindings. Its methods are named after the analogous method from the
        Exodus II C bindings, minus the prefix 'ex_'.

        The ExodusIIWriter instance expects that any multi-dimensional arrays
        are passed as row major (Python convention). The transpose of these
        arrays is passed to the Fortran procedures.

        The optional offset parameter allows passing coordinate lists, node
        lists, element lists, etc., starting from the natural starting number
        0. Because the Exodus II library (older versions) require numbering to
        by > 0, the offset is added to each number in the appropriate lists.

        """
        self.filename = filename
        self.exoid = exoid
        self._o = offset

        pass

    @classmethod
    def new_from_runid(cls, runid, offset=1):
        """Creates a new EXODUS II file instance

        Parameters
        ----------

        runid : str
            The simulation run ID

        Returns
        -------
        ExodusIIWriter : object
            ExodusIIWriter instance

        """
        return cls(*cls.get_exoid(runid), offset=offset)

    @classmethod
    def from_existing(cls, filepath, offset=1):
        """Creates an EXODUS II file instance

        Parameters
        ----------
        filepath : str
            Path to existing file

        Returns
        -------
        ExodusIIWriter : object
            ExodusIIWriter instance

        """
        cpu_ws = np.array([0])
        io_ws = np.array([0])
        exoid, vers, ierr = exolib.py_exopen(filepath, EX_WRITE, cpu_ws, io_ws)
        if ierr:
            raise ExodusIIWriterError("Error creating exodus output")
        return cls(filepath, exoid, offset=offset)

    @staticmethod
    def get_exoid(runid):
        """Get the Exodus II file ID

        Parameters
        ----------
        runid : str
            String used for file name

        """
        cpu_ws = np.array([0])
        io_ws = np.array([0])
        exoname = runid + ".exo"
        exoid, ierr = exolib.py_excre(exoname, EX_CLOBBER, cpu_ws, io_ws)
        if ierr:
            raise ExodusIIWriterError("Error creating exodus output")
        return exoname, exoid

    def close(self):
        """Close the exodus file

        """
        return exolib.py_exclos(self.exoid)

    def update(self):
        """Update the data file.

        """
        return exolib.py_exupda(self.exoid)

    def put_init(self, title, num_dim, num_nodes, num_elem, num_elem_blk,
                    num_node_sets, num_side_sets):
        """Writes the initialization parameters to the EXODUS II file

        Parameters
        ----------
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
        self.dim = num_dim
        ierr = exolib.py_expini(self.exoid, title, num_dim, num_nodes,
                                num_elem, num_elem_blk, num_node_sets,
                                num_side_sets)
        if ierr:
            raise ExodusIIWriterError("Error initializing exodus output")
        return

    def put_coord(self, x, y, z):
        """Write the names of the coordinate arrays

        Parameters
        ----------
        x, y, z : array_like
            x, y, z coordinates

        """
        ierr = exolib.py_expcor(self.exoid, x, y, z)
        if ierr:
            raise ExodusIIWriterError("Error putting nodal coordinates")


    def put_coord_names(self, coord_names):
        """Writes the names of the coordinate arrays to the database.

        Parameters
        ----------
        coord_names : array_like
            Array containing num_dim names (of length MAX_STR_LENGTH) of the
            nodal coordinate arrays.

        """
        coord_names = ["{0:{1}s}".format(x, MAX_STR_LENGTH)[:MAX_STR_LENGTH]
                       for x in coord_names]
        ierr = exolib.py_expcon(self.exoid, coord_names)
        if ierr:
            raise ExodusIIWriterError("Error putting coordinate names")

    def put_map(self, elem_map):
        """Writes out the optional element order map to the database

        Parameters
        ----------
        elem_map : array_like
            The element map

        Notes
        -----
        The following code generates a default element order map and outputs
        it to an open EXODUS II file. This is a trivial case and included just
        for illustration. Since this map is optional, it should be written out
        only if it contains something other than the default map.

        elem_map = []
        for i in range(num_elem):
            elem_map.append(i)
        ExodusIIWriterError.put_map(np.array(elem_map))

        """
        ierr = exolib.py_expmap(self.exoid, elem_map + self._o)
        if ierr:
            raise ExodusIIWriterError("Error putting element map")


    def put_elem_block(self, elem_blk_id, elem_type, num_elem_this_blk,
                       num_nodes_per_elem, num_attr):
        """Write parameters used to describe an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID.

        elem_type : str
            The type of elements in the element block. The maximum length of
            this string is MAX_STR_LENGTH. For historical reasons, this
            string should be all upper case.

        num_elem_this_blk : int
            The number of elements in the element block.

        num_nodes_per_elem : int
            Number of nodes per element in the element block

        num_attr : int
            The number of attributes per element in the element block.

        """
        ierr = exolib.py_expelb(self.exoid, elem_blk_id, elem_type,
                                num_elem_this_blk, num_nodes_per_elem, num_attr)
        if ierr:
            raise ExodusIIWriterError("Error putting element block information")

    def put_prop_names(self, obj_type, num_props, prop_names):
        """Writes property names and allocates space for property arrays used
        to assign integer properties to element blocks, node sets, or side
        sets.

        Parameters
        ----------
        obj_type : int
            The type of object; use on of the following options
            EX_ELEM_BLOCK
            EX_NODE_SET
            EX_SIDE_SET

        num_props : int
            The number of properties

        prop_names : array_like
            Array containing num_props names

        """
        ierr = exolib.py_exppn(self.exoid, obj_type, num_props, prop_names)
        if ierr:
            raise ExodusIIWriterError("Error putting prop names")

    def put_prop(self, obj_type, obj_id, prop_name, value):
        """Stores an integer property value to a single element block, node
        set, or side set.

        Parameters
        ----------
        obj_type : int
            The type of object; use on of the following options
            EX_ELEM_BLOCK
            EX_NODE_SET
            EX_SIDE_SET

        obj_id : int
            The element block, node set, or side set ID

        prop_name : str
            Property name

        value : int
            The value of the property

        """
        ierr = exolib.py_expp(self.exoid, obj_type, obj_id, prop_name, value)
        if ierr:
            raise ExodusIIWriterError("Error putting prop value")

    def put_elem_conn(self, elem_blk_id, connect):
        """writes the connectivity array for an element block

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        connect : array_like
            Connectivity array, list of nodes that define each element in the
            block

        """
        ierr = exolib.py_expelc(self.exoid, elem_blk_id, connect.T + self._o)
        if ierr:
            raise ExodusIIWriterError("Error putting element connectivity")

    def put_elem_attr(self, elem_blk_id, attr):
        """writes the attribute to the

        Parameters
        ----------
        elem_blk_id : int
            The element block ID

        attr : array_like, (num_elem_this_block, num_attr)
            List of attributes for the element block

        """
        ierr = exolib.py_expeat(self.exoid, elem_blk_id, attr.T)
        if ierr:
            raise ExodusIIWriterError("Error putting element attribute")

    def put_node_set_param(self, node_set_id, num_nodes_in_set,
                           num_dist_fact_in_set=0):
        """Writes the node set ID, the number of nodes which describe a single
        node set, and the number of distribution factors for the node set.

        Parameters
        ----------
        node_set_id : int
            The node set ID

        num_nodes_in_set : int
            Number of nodes in set

        num_dist_fact_in_set : int
            The number of distribution factors in the node set. This should be
            either 0 (zero) for no factors, or should equal num_nodes_in_set.

        """
        ierr = exolib.py_expnp(self.exoid, node_set_id, num_nodes_in_set,
                               num_dist_fact_in_set)
        if ierr:
            raise ExodusIIWriterError("Error putting node set params")

    def put_node_set(self, node_set_id, node_set_node_list):
        """Writes the node list for a single node set.

        Parameters
        ----------
        node_ set_id : int
            The node set ID.

        node_set_node_list : array_like
            Array containing the node list for the node set. Internal node IDs
            are used in this list.

        Notes
        -----
        The function put_node_set_param must be called before this routine is
        invoked.

        """
        ierr = exolib.py_expns(self.exoid, node_set_id,
                               node_set_node_list + self._o)
        if ierr:
            raise ExodusIIWriterError("Error putting node set")

    def put_node_set_dist_fact(self, node_set_id, node_set_dist_fact):
        """Writes distribution factors for a single node set

        Parameters
        ----------
        node_ set_id : int
            The node set ID.

        node_set_dist_fact : array_like
            Array containing the distribution factors for each node in the set

        Notes
        -----
        The function put_node_set_param must be called before this routine is
        invoked.

        """
        ierr = exolib.py_expnsd(self.exoid, node_set_id, node_set_dist_fact)
        if ierr:
            raise ExodusIIWriterError("Error putting node set distribution factors")

    def put_side_set_param(self, side_set_id, num_sides_in_set,
                           num_dist_fact_in_set=0):
        """Writes the side set ID, the number of sides (faces on 3-d element,
        edges on 2-d) which describe a single side set, and the number of
        distribution factors on the side set.

        Parameters
        ----------
        side_set_id : int
            The side set ID

        num_sides_in_set : int
            Number of sides in set

        num_dist_fact_in_set : int
            The number of distribution factors in the side set. This should be
            either 0 (zero) for no factors, or should equal num_sides_in_set.

        """
        ierr = exolib.py_expsp(self.exoid, side_set_id, num_sides_in_set,
                               num_dist_fact_in_set)
        if ierr:
            raise ExodusIIWriterError("Error putting side set params")

    def put_side_set(self, side_set_id, side_set_elem_list,
                     side_set_side_list):
        """Writes the side set element list and side set side (face on 3-d
        element types; edge on 2-d element types) list for a single side set.

        Parameters
        ----------
        side_ set_id : int
            The side set ID.

        side_set_elem_list : array_like
            Array containing the elements in the side set. Internal element
            IDs are used in this list

        side_set_side_list : array_like
            Array containing the side in the side set

        Notes
        -----
        The function put_side_set_param must be called before this routine is
        invoked.

        """
        ierr = exolib.py_expss(self.exoid, side_set_id,
                               side_set_elem_list + self._o,
                               side_set_side_list + self._o)
        if ierr:
            raise ExodusIIWriterError("Error putting side set")

    def put_side_set_dist_fact(self, side_set_id, side_set_dist_fact):
        """Writes distribution factors for a single side set

        Parameters
        ----------
        side_ set_id : int
            The side set ID.

        side_set_dist_fact : array_like
            Array containing the distribution factors for each side in the set

        Notes
        -----
        The function put_side_set_param must be called before this routine is
        invoked.

        """
        ierr = exolib.py_expssd(self.exoid, side_set_id, side_set_dist_fact)
        if ierr:
            raise ExodusIIWriterError("Error putting side set distribution factors")

    def put_prop_array(self, obj_type, prop_name, values):
        """Stores an array of (num_elem_blk, num_node_sets, or num_side_sets)
        integer property values for all element blocks, node sets, or side
        sets.

        Parametes
        ---------
        obj_type : int
            The type of object; use on of the following options
            EX_ELEM_BLOCK
            EX_NODE_SET
            EX_SIDE_SET

        prop_name : string
            Property name

        values : array_like
            An array of property values

        """
        ierr = exolib.py_exppa(self.exoid, obj_type, prop_name, values)
        if ierr:
            raise ExodusIIWriterError("Error putting prop array")

    def put_prop(self, obj_type, obj_id, prop_name, value):
        """Stores an integer property value to a single element block, node
        set, or side set.

        Parameters
        ----------
        obj_type : int
            The type of object; use on of the following options
            EX_ELEM_BLOCK
            EX_NODE_SET
            EX_SIDE_SET

        obj_id : int
            The element block, node set, or side set ID

        prop_name : str
            Property name

        Notes
        -----
        The order of the values in the array must correspond to the order in
        which the element blocks, node sets, or side sets were introduced into
        the file. For instance, if the parameters for element block with ID 20
        were written to a file (via put_elem_block) and then parameters for
        element block with ID 10, followed by the parameters for element block
        with ID 30, the first, second, and third elements in the property
        array would correspond to element block 20, element block 10, and
        element block 30,respectively. One should note that this same
        functionality (writing properties to multiple objects) can be
        accomplished with multiple calls to put_prop

        """
        ierr = exolib.py_expp(self.exoid, obj_type, obj_id, prop_name, value)
        if ierr:
            raise ExodusIIWriterError("Error putting prop")

    def put_qa(self, num_qa_records, qa_record):
        """Writes the QA records to the database.

        Parameters
        ----------
        num_qa_records : int
            Then number of QA records

        qa_record : array_like, (num_qa_records, 4)
            Array containing the QA records

        Notes
        -----
        Each QA record contains for MAX_STR_LENGTH-byte character strings. The
        character strings are

          1) the analysis code name
          2) the analysis code QA descriptor
          3) the analysis date
          4) the analysis time

        """
        ierr = exolib.py_expqa(self.exoid, num_qa_records, qa_record.T)
        if ierr:
            raise ExodusIIWriterError("Error putting QA record")

    def put_info(self, info):
        """Writes information records to the database. The records are
        MAX_LINE_LENGTH-character strings.

        Parameters
        ----------
        info : array_like, (num_info, )
            Array containing the information records

        """
        info = ["{0:{1}s}".format(x, MAX_LINE_LENGTH)[:MAX_LINE_LENGTH]
                for x in info]
        ierr = exolib.py_expinf(self.exoid, info)
        if ierr:
            raise ExodusIIWriterError("Error putting information record")

    def put_var_param(self, var_type, num_vars):
        """Writes the number of global, nodal, nodeset, sideset, or element
        variables that will be written to the database.

        Parameters
        ----------
        var_type : str
            Character indicating the type of variable which is described.
            Use one of the following options:
              "g" (or "G")
              "n" (or "N")
              "e" (or "E")
              "m" (or "M")
              "s" (or "S")
            For global, nodal, element, nodeset variables, and sideset
            variables, respectively.

        num_vars : int
            The number of var_type variables that will be written to the
            database.

        """
        if var_type.upper() not in EX_VAR_TYPES:
            raise ExodusIIWriterError(
                "var_type {0} not recognized".format(var_type))
        ierr = exolib.py_expvp(self.exoid, var_type.lower(), num_vars)
        if ierr:
            raise ExodusIIWriterError("Error putting var params")

    def put_var_names(self, var_type, num_vars, var_names):
        """Writes the names of the results variables to the database. The
        names are MAX_STR_LENGTH-characters in length.

        Parameters
        ----------


        Notes
        -----
        The function put_var_param must be called before this function is
        invoked.

        """
        if var_type.upper() not in EX_VAR_TYPES:
            raise ExodusIIWriterError(
                "var_type {0} not recognized".format(var_type))
        # var names must all be of same length due to Fortran restrictions
        var_names = ["{0:{1}s}".format(x, MAX_STR_LENGTH)[:MAX_STR_LENGTH]
                     for x in var_names]
        ierr = exolib.py_expvan(self.exoid, var_type.lower(), var_names)
        if ierr:
            raise ExodusIIWriterError("Error putting var names")


    def put_elem_var_tab(self, num_elem_blk, num_elem_var, elem_var_tab):
        """Writes the EXODUS II element variable truth table to the database.

        The element variable truth table indicates whether a particular
        element result is written for the elements in a particular element
        block. A 0 (zero) entry indicates that no results will be output for
        that element variable for that element block. A non-zero entry
        indicates that the appropriate results will be output.

        Parameters
        ----------
        num_elem_blk : int
            The number of element blocks.

        num_elem_var : int
            The number of element variables.

        elem_var_tab : array_like, (num_elem_blk, num_elem_var)
             A 2-dimensional array containing the element variable truth
             table.

        Notes
        -----
        Although writing the element variable truth table is optional, it is
        encouraged because it creates at one time all the necessary netCDF
        variables in which to hold the EXODUS element variable values. This
        results in significant time savings. See Appendix A for a discussion
        of efficiency issues. Calling the function put_var_tab with an
        object type of "E" results in the same behavior as calling this
        function.

        The function put_var_param (or EXPVP for Fortran) must be called
        before this routine in order to define the number of element
        variables.

        """
        ierr = exolib.py_expvtt(self.exoid, num_elem_blk, num_elem_var,
                                elem_var_tab.T)
        if ierr:
            raise ExodusIIWriterError("Error putting element truth table")

    def put_time(self, time_step, time_value):
        """Writes the time value for a specified time step.

        Parameters
        ----------
        time_step : int
            The time step number.
            This is essentially a counter that is incremented only when
            results variables are output to the data file. The first time step
            is 1.

        time_value : float
            The time at the specified time step.

        """
        ierr = exolib.py_exptim(self.exoid, time_step + self._o, time_value)
        if ierr:
            raise ExodusIIWriterError("Error putting time")

    def put_glob_vars(self, time_step, num_glob_vars, glob_var_vals):
        """Writes the values of all the global variables for a single time step.

        time_step : int
            The time step number, as described under put_time.
            This is essentially a counter that is incremented when results
            variables are output. The first time step is 1.

        num_glob_vars : int
            The number of global variables to be written to the database.

        glob_var_vals : array_like
            Array of num_glob_vars global variable values for the time_stepth
            time step.

        Notes
        -----
        The function put_var_param must be invoked before this call is made.

        """
        ierr = exolib.py_expgv(self.exoid, time_step + self._o,
                               num_glob_vars, glob_var_vals)
        if ierr:
            raise ExodusIIWriterError("Error putting global vars")

    def put_nodal_var(self, time_step, nodal_var_index, num_nodes,
                      nodal_var_vals):
        """Writes the values of a single nodal variable for a single time
        step.

        Parameters
        ----------
        time_step : int
            The time step number, as described under put_time. This is
            essentially a counter that is incremented when results variables
            are output. The first time step is 1.

        nodal_var_index : int
            The index of the nodal variable.
            The first variable has an index of 1.

        num_nodes : int
            The number of nodal points.

        nodal_var_vals : array_like
            Array of num_nodes values of the nodal_var_indexth nodal variable
            for the time_stepth time step.

        Notes
        -----
        The function put_var_param must be invoked before this call is made.

        """
        ierr = exolib.py_expnv(self.exoid, time_step + self._o,
                               nodal_var_index + self._o, num_nodes,
                               nodal_var_vals)
        if ierr:
            raise ExodusIIWriterError("Error putting nodal vars")

    def put_elem_var(self, time_step, elem_var_index, elem_blk_id,
                     num_elem_this_blk, elem_var_vals):
        """Writes the values of a single elemental variable for a single time
        step.

        Parameters
        ----------
        time_step : int
            The time step number, as described under put_time. This is
            essentially a counter that is incremented when results variables
            are output. The first time step is 1.

        elem_var_index : int
            The index of the element variable.
            The first variable has an index of 1.

        elem_blk_id : int
            The element block ID

        num_elem_this_blk : int
            The number of elements in the given element block

        elem_var_vals : array_like
            Array of num_elem_this_blk values of the elem_var_indexth element
            variable for the element block with ID of elem_blk_id at the
            time_stepth time step

        Notes
        -----
        The function put_var_param must be invoked before this call is
        made.

        It is recommended, but not required, to write the element variable
        truth table before this function is invoked for better efficiency.

        """
        ierr = exolib.py_expev(self.exoid, time_step + self._o,
                               elem_var_index + self._o, elem_blk_id,
                               num_elem_this_blk, elem_var_vals)
        if ierr:
            raise ExodusIIWriterError("Error putting element vars")
