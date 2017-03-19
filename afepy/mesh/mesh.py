import sys
import numpy as np
try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

import readers as readers
from utils import *
from consts import *

from tools.logger import ConsoleLogger as logger
from tools.misc import isstr, getopt, dof_id
from tools.errors import AFEPYError
import geom as geom

class NodesetRepository(OrderedDict):
    @property
    def exo_ids(self):
        return [v.exo_id for v in self.values()]
class Nodeset:
    def __init__(self, name, exo_id, node_ids):
        self.name = name
        self.exo_id = exo_id
        self.node_ids = np.array(node_ids)

class SidesetRepository(OrderedDict):
    @property
    def exo_ids(self):
        return [v.exo_id for v in self.values()]
class Sideset:
    def __init__(self, name, exo_id, surfaces):
        self.name = name
        self.exo_id = exo_id
        self.surfaces = surfaces

class BlockRepository(OrderedDict):
    @property
    def exo_ids(self):
        return [v.exo_id for v in self.values()]
    def get_block_by_elem_id(self, elem_id):
        for eb in self.values():
            if elem_id in eb.elem_ids:
                return eb
class ElementBlock:
    def __init__(self, name, elem_ids, exo_id):
        self.name = name
        self.exo_id = exo_id
        self.elem_ids = np.array(elem_ids)
        self.num_elem = len(elem_ids)

class MeshBase(object):
    """Abstract mesh base class

    *** Should not be instantiated directly ***

    """
    def __init__(self, type, num_dim, coords, connect, node_num_map, elem_num_map):
        self.type = type
        self.ndim = num_dim
        self.mats = {}
        self.nodesets = NodesetRepository()
        self.sidesets = SidesetRepository()
        self.blocks = BlockRepository()

        self.coords = coords
        self.node_ids = np.arange(coords.shape[0], dtype=np.int)
        self.node_num_map = node_num_map

        self.connect = connect
        self.elem_ids = np.arange(connect.shape[0], dtype=np.int)
        self.elem_num_map = elem_num_map

    @property
    def mesh(self):
        return self

    @property
    def num_elems_per_block(self):
        return np.array([eb.num_elem for eb in self.blocks])

    @property
    def elems_per_block(self):
        """Return the element IDS of each block

        Returns
        -------
        a : ndarray, (num_elem_blk,)
            a[i] is the number of elements in block i

        Notes
        -----
        Elements are stored contiguously by block.  Using this function,
        the elements in a block can be isolated.

        """
        return [eb.elem_ids for eb in self.element_blocks]

    @property
    def elem_blk_ids(self):
        return [elem_blk.exo_id for elem_blk in self.element_blocks]

    @property
    def element_blocks(self):
        return self.blocks.values()

    def num_elem_in_block(self, elem_blk_id):
        return self.blocks[elem_blk_id].num_elem

    def dof_map(self, node):
        return self.node_num_map[node]

    @property
    def num_dim(self):
        """Return the dimension"""
        return self.ndim

    @property
    def num_coord(self):
        """Return the dimension"""
        return self.ndim

    @property
    def num_node(self):
        """Return the number of nodes"""
        return self.coords.shape[0]

    @property
    def num_cell(self):
        """ Returns the number of elements."""
        return self.connect.shape[0]

    @property
    def extremum(self):
        """Max X, Y[, Z] position"""
        return bounding_box(self.coords)

    @property
    def elem_num_map_exo(self):
        return np.array([k for k in sorted(self.elem_num_map,
                                           key=lambda x: self.elem_num_map[x])])

    @property
    def node_num_map_exo(self):
        return np.array([k for k in sorted(self.node_num_map,
                                           key=lambda x: self.node_num_map[x])])

    @property
    def nodesets_exo(self):
        """Return the number of nodes"""
        return [(ns.exo_id, ns.node_ids) for ns in self.nodesets.values()]

    @property
    def sidesets_exo(self):
        """Return the side set definitions"""
        return [(ss.exo_id, ss.surfaces[:, 0], ss.surfaces[:, 1])
                for ss in self.sidesets.values()]

    def ElementBlock(self, name=None, elements=None, exo_id=None, mapped=1):
        """Assign elements to an element block"""
        if name is None:
            i = 1
            while True:
                name = "Block-{0}".format(i)
                if name not in self.blocks:
                    break
                i += 1
                if i > MAX_NUM_SETS:
                    raise AFEPYError("maximum number of blocks exceeded")
        if name in self.blocks:
            raise AFEPYError("{0}: element block already exists".format(name))

        if exo_id is None:
            exo_id = BLOCK_ID_START
            while True:
                if exo_id not in self.blocks.exo_ids:
                    break
                exo_id += 1
                if exo_id > MAX_NUM_SETS+BLOCK_ID_START:
                    raise AFEPYError("maximum number of blocks exceeded")

        if isstr(elements):
            if elements.lower() == "all":
                elements = np.array(range(self.num_cell), dtype=np.int)

            elif elements.lower() == "unassigned":
                assigned = []
                for elem_blk in self.element_blocks:
                    assigned.extend(elem_blk.elem_ids)
                elements = list(set(self.elem_ids) - set(assigned))
                elements = np.array(elements, dtype=np.int)

            else:
                raise AFEPYError("{0}: unrecognized option".format(elements))

        else:
            if mapped:
                elements = [self.elem_num_map[e] for e in elements]
            elements = np.array(elements, dtype=np.int)

        self.blocks[name] = ElementBlock(name, elements, exo_id)
        return self.blocks[name]

    def run_diagnostics(self):
        self.find_orphans()

    def find_orphans(self):
        orphans = []
        for elem_id in range(self.num_cell):
            orphaned = True
            for elem_blk in self.element_blocks:
                if elem_id in elem_blk.elem_ids:
                    orphaned = False
                    break
            if orphaned:
                orphans.append(elem_id)
        if orphans:
            o = ", ".join("{0}".format(x) for x in orphans)
            raise AFEPYError("Orphaned elements detected.  All elements "
                             "must be assigned to an element block.  "
                             "Orphaned elements:\n {0}".format(o))

    def Nodeset(self, name=None, nodes=None, region=None, exo_id=None,
                tol=None, mapped=1):
        """Assign nodesets to the mesh

        """
        if name is None:
            i = 1
            while True:
                name = "Nodeset-{0}".format(i)
                if name not in self.nodesets:
                    break
                i += 1
                if i > MAX_NUM_SETS:
                    raise AFEPYError("maximum number of nodesets exceeded")
        if name in self.nodesets:
            raise AFEPYError("{0}: nodeset already exists".format(name))

        if exo_id is None:
            exo_id = NSET_ID_START
            while True:
                if exo_id not in self.nodesets.exo_ids:
                    break
                exo_id += 1
                if exo_id >= MAX_NUM_SETS+NSET_ID_START:
                    raise AFEPYError("maximum number of nodesets exceeded")
        if exo_id in self.nodesets.exo_ids:
            raise AFEPYError("{0}: nodeset exo_id already exists".format(name))

        ns_nodes = []
        if nodes is not None:
            try:
                if mapped:
                    ns_nodes = [self.node_num_map[node] for node in nodes]
                else:
                    ns_nodes = [node for node in nodes]
            except KeyError:
                raise AFEPYError("invalid node number for node "
                                 "set {0}".format(name))

        if region is not None:
            nodes = self.nodes_in_region(region, tol=tol)
            if not nodes:
                raise AFEPYError("no nodes found in region {0}".format(region))
            ns_nodes.extend(nodes)

        self.nodesets[name] = Nodeset(name, exo_id, ns_nodes)
        return self.nodesets[name]

    def nodes_in_region(self, region, tol=None):
        found_nodes = []
        #tjfulle: tol should be based on characteristic element length
        tol = tol or 1.E-08
        for r in region.split("&&"):
            axis, pos = self.get_axis_pos(r)
            nodes, els = self.members_at_position(axis, pos, tol=tol)
            found_nodes.append(set(nodes))
        nodes = found_nodes[0]
        for others in found_nodes[1:]:
            nodes = nodes & others
        return list(nodes)

    def Sideset(self, name, surfaces=None, exo_id=None, region=None, mapped=1):
        """Assign side sets to the mesh

        Parameters
        ----------
        surfaces : ndarray
            Side set specification
            sset[i, j] - jth face of element i
        exo_id : int
            Side set identifying integer

        """
        if name is None:
            i = 1
            while True:
                name = "Sideset-{0}".format(i)
                if name not in self.sidesets:
                    break
                i += 1
                if i > MAX_NUM_SETS:
                    raise AFEPYError("maximum number of sidesets exceeded")
        if name in self.sidesets:
            raise AFEPYError("{0}: sideset already exists".format(name))

        if exo_id is None:
            exo_id = SSET_ID_START
            while True:
                if exo_id not in self.sidesets.exo_ids:
                    break
                exo_id += 1
                if exo_id >= MAX_NUM_SETS+SSET_ID_START:
                    raise AFEPYError("maximum number of sidesets exceeded")
        if exo_id in self.sidesets.exo_ids:
            raise AFEPYError("{0}: sideset exo_id already exists".format(name))

        sset_surfs = []
        if surfaces is not None:
            for (i, item) in enumerate(surfaces):
                try:
                    elem, face = item
                except ValueError:
                    raise AFEPYError("bad sideset definition")
                try:
                    if mapped:
                        elem = self.elem_num_map[elem]
                    sset_surfs.extend([elem, face-1])
                except KeyError:
                    raise AFEPYError("{0}: element not in mesh".format(elem))

        if region is not None:
            # look for acceptable domain names
            if self.type != "grid":
                exit("cannot yet set sideset by region")

            try:
                axis = DOMAINS[region.upper()]
            except KeyError:
                raise AFEPYError("{0}: invalid sideset region".format(surfaces))

            nodes, els = self.members_at_position(axis[0], self.extremum[axis])

            # Side sets are defined on an element face.  Loop through elements,
            # store the element number, face number, and the traction
            face = geom.face(self.num_coord, self.connect.shape[1], region)
            for elem_num in els:
                sset_surfs.extend([elem_num, face])

        sset_surfs = np.array(sset_surfs).reshape(-1, 2)
        self.sidesets[name] = Sideset(name, exo_id, sset_surfs)
        return self.sidesets[name]

    def get_axis_pos(self, region):

        R = region.upper()
        try:
            R, pos = R.split("==", 1)
            pos = float(pos)
            axis = {"X": 0, "Y": 1, "Z": 2}[R.strip().upper()]

        except ValueError:
            try:
                axis, b  = DOMAINS[R]
                pos = self.extremum[(axis, b)]
            except KeyError:
                raise AFEPYError("{0}: invalid nodeset region".format(region))

        return axis, pos

    def members_at_position(self, axis, pos, tol=1E-08):
        """Returns nodes (and connected elements) whose position on the axis
        fall on pos.

        Parameters
        ----------
        axis : int
            Coordinate axis {x: 0, y: 1, z: 2}

        pos : float
            position

        """
        return members_at_position(self.coords, self.connect, axis, pos, tol=tol)

    def check_elem_block(self, elem_block_id, prop=None):
        if elem_block_id not in self.blocks:
            return 1
        if prop is None:
            return 0
        if prop not in self.blocks[elem_block_id]:
            return 2

    def get_node_ids(self, nodes, nodeset, region):
        if all([x is None for x in (nodeset, nodes, region)]):
            # require one
            raise AFEPYError("1 of [nodeset, nodes, region] keywords required")

        if len([x for x in (nodeset, nodes, region) if x is not None]) > 1:
            raise AFEPYError("1 of [nodeset, nodes, region] keywords required")

        if nodeset:
            try:
                node_ids = self.nodesets[nodeset].node_ids
            except KeyError:
                raise AFEPYError("{0}: invalid node set ID".format(nodeset))

        elif nodes:
            node_ids = [self.dof_map(node) for node in nodes]

        else:
            node_ids = self.nodes_in_region(region)

        return node_ids

    @classmethod
    def mesh_grid_2D(cls, nx=2, ny=2, lx=1., ly=1.):
        """Uniform 2D grid mesh class:

        Initializes the mesh structure.

        Parameters
        ----------
        nx, ny : int
            Number of nodes in the x and y directions, respectively
        lx, ly : real
            Lengths in x and y directions, respectively

        """
        # Initialize nodal coordinates.
        logger.debug("constructing mesh... ", end=" ")
        (coords, connect, node_num_map,
         elem_num_map) = gen_mesh_grid_2D_simple((nx, ny), (lx, ly))
        logger.debug("done")
        return cls("grid", 2, coords, connect, node_num_map, elem_num_map)

    @classmethod
    def mesh_grid_3D(cls, nx=2, ny=2, nz=2, lx=1., ly=1., lz=1., **options):
        """Uniform 3D grid mesh class:

        Initializes the mesh structure.

        Parameters
        ----------
        nx, ny, nz : int
            Number of nodes in the x, y, and z directions, respectively
        lx, ly, lz : real
            Lengths in x, y, and z directions, respectively

        """
        # Initialize nodal coordinates.
        logger.debug("constructing mesh... ", end=" ")
        (coords, connect, node_num_map,
         elem_num_map) = gen_mesh_grid((nx, ny, nz), (lx, ly, lz), **options)
        logger.debug("done")
        return cls("grid", 3, coords, connect, node_num_map, elem_num_map)

    @classmethod
    def from_xml(cls, filename=None, string=None):

        xmesh = readers.parse_xml(filename=filename, string=string)
        mesh = cls("unstructured", xmesh.num_dim, xmesh.coords, xmesh.connect,
                   xmesh.node_num_map, xmesh.elem_num_map)

        for eb in xmesh.blocks:
            mesh.ElementBlock(name=eb.name, exo_id=eb.exo_id, elements=eb.elements)

        # assign sets
        for ss in xmesh.sidesets:
            mesh.Sideset(name=ss.name, exo_id=ss.exo_id, surfaces=ss.data)

        for ns in xmesh.nodesets:
            mesh.Nodeset(name=ns.name, exo_id=ns.exo_id, nodes=ns.data)

        return mesh

    @classmethod
    def from_genesis(cls, filename):

        gmesh = readers.parse_genesis(filename)
        mesh = cls("unstructured", gmesh.num_dim, gmesh.coords, gmesh.connect,
                   gmesh.node_num_map, gmesh.elem_num_map)

        for eb in gmesh.blocks:
            mesh.ElementBlock(name=eb.name, exo_id=eb.exo_id,
                              elements=eb.elements, mapped=0)

        # assign sets
        for ss in gmesh.sidesets:
            mesh.Sideset(name=ss.name, exo_id=ss.exo_id, surfaces=ss.data, mapped=0)

        for ns in gmesh.nodesets:
            mesh.Nodeset(name=ns.name, exo_id=ns.exo_id, nodes=ns.data, mapped=0)

        return mesh

    def toxml(self, filename):
        from writers import XML
        a = XML.from_mesh(self)
        a.write(filename)
