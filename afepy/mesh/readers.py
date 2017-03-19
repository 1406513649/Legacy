import os
import re
import gzip
import numpy as np
import xml.dom.minidom as xdom
from os.path import splitext

from consts import *
from geom import DOMAINS, get_elem_type
from utils import bounding_box, gen_mesh_grid, members_at_position
import sys
from tools.misc import Namespace
from tools.errors import AFEPYError

# *** NOTE ***
# If ever in the parser you are confused as to why there is a '-1',
# it is likely due to the fact that input files are given with 1 based
# numbering, whereas the actual programming is 0 based (this is python
# after all)

def Int(item):
    return int(Float(item))

def Float(item):
    try: return float(item)
    except ValueError: return None

def get_dof(dof):
    dofs = {"X": 0, "Y": 1, "Z": 2, "ALL": "ALL"}
    try: return Int(dof)
    except (TypeError, ValueError): return dofs.get(dof.upper())

def parse_xml(filename=None, string=None):
    if string is None and filename is None:
        raise AFEPYError("parse_xml must receive a filename or string argument")
    if string is not None and filename is not None:
        raise AFEPYError("parse_xml must receive only 1 of "
                         "filename or string argument")
    if string:
        doc = xdom.parseString(string)
    elif filename.endswith(".gz"):
        f = gzip.open(filename, "rb")
        doc = xdom.parseString(f.read())
        f.close()
    else:
        doc = xdom.parse(filename)

    root = doc.getElementsByTagName("Mesh")[0]
    (num_dim, nodes, conn, nsdict, ssdict, blkdict,
     node_num_map, elem_num_map) = parse_xml_mesh(root)

    # format sidesets
    sidesets = []
    for (name, v) in ssdict.items():
        s = Namespace("Sideset", name=name, exo_id=v["exo_id"], data=v["surface"])
        sidesets.append(s)

    nodesets = []
    for (name, v) in nsdict.items():
        s = Namespace("Nodeset", name=name, exo_id=v["exo_id"], data=v["nodes"])
        nodesets.append(s)

    blocks = []
    for (name, block) in blkdict.items():
        b = Namespace("ElementBlock", name=name, exo_id=block["exo_id"],
                      elem_type=block["elem_type"], elements=block["elements"])
        blocks.append(b)

    return Namespace("Mesh", coords=nodes, connect=conn, num_dim=num_dim,
                     node_num_map=node_num_map, sidesets=sidesets,
                     nodesets=nodesets, elem_num_map=elem_num_map,
                     blocks=blocks)

def parse_xml_mesh(mesh):
    """Parse the (single) Mesh element

    Notes
    -----
    <Mesh>
      <Vertices> ... </Vertices>
      <Connectivity> ... </Connectivity>
      <Sideset> ... </Sideset>
      <Nodeset> ... </Nodeset>
    </Mesh>

    """
    mesh_types = ("DEFAULT", "GRID")
    grid = mesh.getAttribute("type")
    mesh_type = get_attribute(mesh, "type", "DEFAULT").upper()
    if mesh_type not in mesh_types:
        raise AFEPYError("{0}: unrecognized mesh type".format(mesh_type))

    if mesh_type == "DEFAULT":
        node_num_map, nodes, num_dim = parse_nodes(mesh)
        elem_num_map, conn, eblx = parse_conn(mesh, num_dim, node_num_map)
        nodes = nodes[:, :num_dim]

    elif mesh_type == "GRID":
        num_dim, nodes, conn, node_num_map, elem_num_map = parse_grid_mesh(mesh)

    # find node sets, side sets
    ns = parse_ns(mesh, nodes, conn, node_num_map) or {}
    ss = parse_ss(mesh, elem_num_map) or {}
    blx = parse_blocks(mesh, num_dim, conn, elem_num_map)

    for k in eblx:
        if k in blx:
            raise AFEPYError("Duplicate block entry {0}".format(k))
    blx.update(eblx)

    return (num_dim, nodes[:, :num_dim], conn, ns, ss,
            blx, node_num_map, elem_num_map)

def parse_grid_mesh(mesh):
    """Parse the grid mesh

    """
    # get the grid
    grid = mesh.getElementsByTagName("Grid")
    if not grid:
        raise AFEPYError("No Mesh.Grid element found")
    if len(grid) > 1:
        raise AFEPYError("Only 1 Mesh.Grid element supported")

    grid = grid[0]
    shape = grid.getAttribute("shape")
    if not shape:
        raise AFEPYError("no shape attribute found for Mesh.Grid")
    shape = tolist(shape, dtype=Int)
    num_dim = len(shape)

    lengths = grid.getAttribute("lengths")
    if not lengths:
        raise AFEPYError("no lengths attribute found for Mesh.Grid")
    lengths = tolist(lengths, dtype=Float)
    if len(lengths) != num_dim:
        raise AFEPYError("len(Mesh.Grid.lengths) must equal num_dim")

    nodes, conn = gen_mesh_grid(shape, lengths)
    node_num_map = dict([(i+1, i) for i in range(nodes.shape[0])])
    elem_num_map = dict([(i+1, i) for i in range(conn.shape[0])])
    return num_dim, nodes, conn, node_num_map, elem_num_map

def parse_nodes(mesh):
    """Parse the (single) Nodes element

    Notes
    -----
    <Vertices dimension="int">
      int float [float [float]]
              ...
    </Vertices>

    """
    els = mesh.getElementsByTagName("Vertices")
    if not els:
        return
    if len(els) > 1:
        raise AFEPYError("Only one Vertices block supported")
    dimension = els[0].getAttribute("dimension")
    if dimension is None:
        raise AFEPYError("Missing Vertices.dimension attribute")
    dimension = Int(dimension)
    nodes = child_data_to_array(els[0], np.float64)

    # nodes given as
    # node_num  x   y   [z]
    # reorder them in ascending node number
    node_nums = []
    for node_num in np.array(nodes[:, 0], dtype=np.int):
        if node_num in node_nums:
            raise AFEPYError("{0}: duplicate node number".format(node_num))
        node_nums.append(node_num)
    node_nums = np.array(node_nums)
    node_num_map = {}
    for (i, n) in enumerate(node_nums):
        node_num_map[n] = i
    nodes = nodes[:, 1:dimension+1]
    return node_num_map, nodes, dimension

def parse_conn(mesh, num_dim, node_num_map):
    """Parse the (single) Connectivity element

    Notes
    -----
    <Connectivity offsets="int">
      int int ... int
           ...
    </Connectivity>

    """
    els = mesh.getElementsByTagName("Connectivity")
    if not els:
        return

    N = 0
    _conn = []
    elem_num_map = {}
    num_elem = 0
    blx = {}
    for el in els:
        offsets = Int(el.getAttribute("offsets"))
        conn = child_data_to_array(el, np.int32)
        elem_nums = conn[:, 0]
        conn = conn[:, 1:]
        for (i, nodes) in enumerate(conn):
            elem_num_map[elem_nums[i]] = num_elem
            for (j, n) in enumerate(nodes):
                try:
                    nodes[j] = node_num_map[n]
                except KeyError:
                    raise AFEPYError("{0}: node not defined".format(n))
            conn[i] = nodes
            num_elem += 1
        if conn.shape[1] != offsets:
            raise AFEPYError("incorrect offsets")
        _conn.append(conn)
        N = max(N, offsets)
        block = el.getAttribute("block")
        if block:
            blx[block] = {"name": block,
                          "exo_id": BLOCK_ID_START+500+len(blx),
                          "elem_type": get_elem_type(num_dim, offsets),
                          "elements": elem_nums}

    elem_num = 0
    connect = -np.ones((num_elem, N), dtype=np.int32)
    for item in _conn:
        for (i, nodes) in enumerate(item):
            connect[elem_num, :len(nodes)] = nodes
            elem_num += 1

    return elem_num_map, connect, blx

def parse_ns(mesh, coords, conn, node_num_map):
    """Parse the Nodeset elements

    Notes
    -----
    <Nodeset exo_id="int">
      int int ... int
           ...
    </Nodeset>

    """
    els = mesh.getElementsByTagName("Nodeset")
    if not els:
        return
    nsdict = {}
    for el in els:
        attributes = dict(el.attributes.items())
        exo_id = attributes.get("exo_id")
        if exo_id is not None:
            exo_id = Int(exo_id)
        name = attributes.get("name")
        if all([x is None for x in (exo_id, name)]):
            raise AFEPYError("Nodeset requires at least one "
                             "of name or exo_id attribute")
        if name is None:
            i = i
            while True:
                name = "Nodeset-{0}".format(i)
                if name not in nsdict:
                    break
                if i > MAX_NUM_SETS:
                    raise AFEPYError("maximum number of nodesets exceeded")
        if name in nsdict:
            raise AFEPYError("{0}: duplicate nodeset".format(exo_id))

        if exo_id is None:
            exo_id = NSET_ID_START
            while True:
                if exo_id not in [v["exo_id"] for (k,v) in nsdict.items()]:
                    break
                exo_id += 1
                if exo_id > MAX_NUM_SETS+NSET_ID_START:
                    raise AFEPYError("maximum number of nodesets exceeded")

        axis = find_region(el)
        if axis:
            box = bounding_box(coords)
            nodes, els = members_at_position(coords, conn, axis[0], box[axis])
        else:
            # nodesets are 1 based in the input file, convert to zero based
            # through the node_num_map
            nodes = child_data_to_array(el, np.int, flatten=1)
            nodes = np.array(nodes)
            for n in nodes:
                if n not in node_num_map:
                    raise AFEPYError("Nodeset '{0}' references "
                                     "nonexistent nodes".format(name))

        nsdict[name] = {"name": name, "exo_id": exo_id, "nodes": nodes}

    return nsdict

def parse_ss(mesh, elem_num_map):
    """Parse the Sideset elements

    Notes
    -----
    <Sideset exo_id="int">
      int int
        ...
    </Sideset>

    """
    els = mesh.getElementsByTagName("Sideset")
    if not els:
        return
    ssdict = {}
    for el in els:
        attributes = dict(el.attributes.items())
        exo_id = attributes.get("exo_id")
        if exo_id is not None:
            exo_id = Int(exo_id)
        name = attributes.get("name")
        if all([x is None for x in (exo_id, name)]):
            raise AFEPYError("Sideset requires at least one "
                             "of name or exo_id attribute")
        if name is None:
            i = i
            while True:
                name = "Sideset-{0}".format(i)
                if name not in nsdict:
                    break
                if i > MAX_NUM_SETS:
                    raise AFEPYError("maximum number of sidesets exceeded")
        if name in ssdict:
            raise AFEPYError("{0}: duplicate sideset".format(exo_id))

        if exo_id is None:
            exo_id = SSET_ID_START
            while True:
                if exo_id not in [v["exo_id"] for (k,v) in ssdict.items()]:
                    break
                exo_id += 1
                if exo_id > MAX_NUM_SETS+SSET_ID_START:
                    raise AFEPYError("maximum number of sidesets exceeded")

        sideset = child_data_to_array(el, np.int, flatten=True)
        if sideset.size % 2 != 0:
            raise AFEPYError("Sidesets must be specified as "
                             "'elem_id face_id' pairs")
        sideset = sideset.reshape(sideset.size/2, 2)
        for (i, elem_face) in enumerate(sideset):
            if elem_face[0] not in elem_num_map:
                raise AFEPYError("'{0}': element not in mesh".format(elem_face[0]))
        ssdict[name] = {"name": name, "exo_id": exo_id, "surface": sideset}
    return ssdict

def parse_blocks(mesh, num_dim, connect, elem_num_map):
    """Parse the Block elements

    Notes
    -----
    <ElementBlock exo_id="int">
      contents
    </ElementBlock>

    contents can be

      o generate start end [interval]
      o all
      o int int ... int
             ...

    """
    els = mesh.getElementsByTagName("ElementBlock")
    if not els:
        return {}

    blocks = {}
    assigned = []
    for el in els:
        attributes = dict(el.attributes.items())
        exo_id = attributes.get("exo_id")
        if exo_id is not None:
            exo_id = Int(exo_id)
        name = attributes.get("name")
        if all([x is None for x in (exo_id, name)]):
            raise AFEPYError("ElementBlock requires at least one "
                             "of name or exo_id attribute")
        if name is None:
            i = 1
            while True:
                name = "Block-{0}".format(i)
                if name not in blocks:
                    break
                if i > MAX_NUM_SETS:
                    raise AFEPYError("maximum number of element blocks exceeded")
        if name in blocks:
            raise AFEPYError("{0}: duplicate block exo_id".format(exo_id))

        if exo_id is None:
            exo_id = BLOCK_ID_START
            while True:
                if exo_id not in [v["exo_id"] for (k,v) in blocks.items()]:
                    break
                exo_id += 1
                if exo_id > MAX_NUM_SETS+BLOCK_ID_START:
                    raise AFEPYError("maximum number of element blocks exceeded")

        blocks[name] = {"name": name, "exo_id": exo_id}
        block = child_data_to_list(el)
        # check for special arguments
        elems = []
        for line in block:
            if line[0].lower() == "all":
                elems = elem_num_map.keys()
                break
            if line[0].lower() == "unassigned":
                elems.extend([x for x in elem_num_map.keys() if x not in assigned])
                break
            if line[0].lower() == "generate":
                line[1:] = [Int(x) for x in line[1:]]
                try:
                    xi, xf, inc = line[1:]
                except ValueError:
                    xi, xf = line[1:]
                    inc = 1
                elems.extend(range(xi, xf+1, inc))
            else:
                elems.extend([Int(x) for x in line])

        num_node_per_elem = None
        for elem in elems:
            if elem not in elem_num_map:
                raise AFEPYError("block '{0}' references "
                                 "non-existent elements".format(name))
            assigned.append(elem)
            nodes = [i for i in connect[elem_num_map[elem]] if i >= 0]
            if num_node_per_elem is None:
                num_node_per_elem = len(nodes)
            elif num_node_per_elem != len(nodes):
                raise AFEPYError("All elements in block '{0}' must have "
                                 "same number of nodes".format(name))

        blocks[name]["elements"] = np.array(elems, dtype=np.int)
        elem_type = el.getAttribute("elem_type")
        if not elem_type.strip():
            elem_type = get_elem_type(num_dim, num_node_per_elem)
        blocks[name]["elem_type"] = elem_type

    return blocks


def child_nodes_to_dict(el, dtype=None, upcase=False):
    node_dict = {}
    for child in el.childNodes:
        if child.nodeType == child.TEXT_NODE:
            continue
        data = " ".join(x.strip() for x in child.firstChild.data.split("\n")
                        if x.split())
        if dtype is not None:
            data = dtype(data)
        if upcase:
            name = child.nodeName.upper()
        else:
            name = child.nodeName
        node_dict[name] = data
    return node_dict


def find_region(el):
    if el.nodeType != el.ELEMENT_NODE:
        return
    data = " ".join(el.firstChild.data.split("\n")).strip()
    return DOMAINS.get(data.upper())


def child_data_to_array(el, dtype, flatten=False):
    array = child_data_to_list(el, flatten=flatten)
    if array is not None:
        array = np.array(array, dtype=dtype)
    return array


def child_data_to_list(el, flatten=False, dtype=str):
    if el.nodeType != el.ELEMENT_NODE:
        return
    data = []
    elc = el.firstChild
    for line in elc.data.split("\n"):
        if not line.split():
            continue
        data.append([dtype(x) for x in re.split("[\, ]", line) if x.split()])
    if flatten:
        data = [x for row in data for x in row]
    return data


def get_attribute(element, attr, default, dtype=str):
    if dtype == int: dtype = Int
    elif dtype == float: dtype = Float
    try: val = element.attributes[attr].value
    except KeyError: val = default
    return dtype(val)

def tolist(string, dtype=str):
    return [dtype(x) for x in re.split(r"[\, ]", string) if x.split()]

def parse_genesis(filename):
    from exojac import ExodusIIFile
    exo = ExodusIIFile(filename, mode="r")
    num_dim = exo.num_dim

    N = 0
    blocks = []
    blk_conn = []
    num_elem = 0
    for elem_blk_id in exo.elem_blk_ids:
        info = exo.get_elem_block(elem_blk_id)
        elem_type, num_elem_this_blk, num_nodes_per_elem, num_attr = info
        N = max(N, num_nodes_per_elem)
        name = "Block-{0}".format(elem_blk_id)
        elements = np.arange(num_elem, num_elem_this_blk)
        b = Namespace("ElementBlock", name=name, exo_id=elem_blk_id,
                      elem_type=elem_type,
                      elements=elements, num_nodes_per_elem=num_nodes_per_elem)
        blocks.append(b)
        num_elem += num_elem_this_blk

        # block connectivity
        blk_conn.extend(exo.get_elem_conn(elem_blk_id))

    # Internally, only one connection is used for all blocks
    connect = np.zeros((num_elem, N), dtype=np.int32)
    for (elem_num, elem_nodes) in enumerate(blk_conn):
        connect[elem_num, :len(elem_nodes)] = elem_nodes

    # Exodus is 1 based.
    connect = np.array(connect) - 1

    # format sidesets
    sidesets = []
    for side_set_id in exo.side_set_ids:
        name = "Sideset-{0}".format(side_set_id)
        surfaces = exo.get_side_set(side_set_id)
        s = Namespace("Sideset", name=name, exo_id=side_set_id, data=surfaces)
        sidesets.append(s)

    nodesets = []
    for node_set_id in exo.node_set_ids:
        name = "Nodeset-{0}".format(node_set_id)
        nodes = exo.get_node_set(node_set_id)
        s = Namespace("Nodeset", name=name, exo_id=node_set_id, data=nodes)
        nodesets.append(s)

    nodes = exo.get_coord()
    node_num_map = dict([(n, i) for (i, n) in enumerate(exo.node_num_map)])
    elem_num_map = dict([(n, i) for (i, n) in enumerate(exo.elem_num_map)])

    return Namespace("Mesh", coords=nodes, connect=connect,
                     num_dim=num_dim, node_num_map=node_num_map, sidesets=sidesets,
                     nodesets=nodesets, elem_num_map=elem_num_map,
                     blocks=blocks)


def parse_gmsh(filename):
    lines = [line for line in open(filename).readlines() if line.split()]
    version = lines[0].split()[1]
    try:
        num_dim = int(lines[1].split()[1])
    except IndexError:
        raise AFEPYError("failed to parse number of dimensions "
                         "from {0}".format(filename))

    assert lines[2].strip() == "Vertices"
    num_node = int(lines[3])
    nodes = []
    for (i, line) in enumerate(lines[4:], 4):
        if re.search("(?i)^[A-Z]", line.strip()):
            break
        nodes.append([float(x) for x in line.split()][:num_dim])
    nodes = np.array(nodes)
    assert nodes.shape[0] == num_node

    elem_type = lines[i].strip().lower()
    nc = {"tet": 4, "hex": 8, "tri": 3, "qua": 4}[elem_type[:3]]
    num_elem = int(lines[i+1])
    elems = []
    for line in lines[i+2:]:
        if re.search("(?i)^[A-Z]", line.strip()):
            break
        elems.append([int(x) for x in line.split()][:nc])
    elems = np.array(elems)
    assert elems.shape[0] == num_elem, "{0}, {1}".format(elems.shape[0], num_elem)

    node_num_map = dict([(i+1, i) for i in range(nodes.shape[0])])
    elem_num_map = dict([(i+1, i) for i in range(elems.shape[0])])

    return Namespace("Mesh", coords=nodes, connect=elems,
                     num_dim=num_dim, node_num_map=node_num_map, sidesets=sidesets,
                     nodesets=nodesets, elem_num_map=elem_num_map,
                     blocks={})

if __name__ == "__main__":

    m = """<?xml version="1.0" ?>
<Mesh version="1.0">
  <Vertices dimension="2">
    1  0.000000000000000000  0.000000000000000000
    2  5.000000000000000000  0.000000000000000000
    3 10.000000000000000000  0.000000000000000000
    4  0.000000000000000000  5.000000000000000000
    5  5.500000000000000000  5.000000000000000000
    6 10.000000000000000000  5.000000000000000000
    7  0.000000000000000000 10.000000000000000000
    8  5.000000000000000000 10.000000000000000000
    9 10.000000000000000000 10.000000000000000000
  </Vertices>
  <Connectivity offsets="4">
    1 1 2 5 4
    2 2 3 6 5
    3 4 5 8 7
  </Connectivity>
  <Connectivity offsets="3">
    4 5 6 8
    5 5 8 9
  </Connectivity>
  <ElementBlock name="B1">
    1 2 3
  </ElementBlock>
  <ElementBlock name="B2">
    unassigned
  </ElementBlock>
</Mesh>
"""

    a = parse_xml(string=m)
    print a
    print a.blocks[0].elem_type
    print a.blocks[0].elements
    print a.blocks[1].elem_type
    print a.blocks[1].elements
