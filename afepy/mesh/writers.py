import numpy as np
import xml.dom.minidom as xdom
from os.path import splitext
from readers import parse_xml

INDENT = 2
def arrtostr2(a, fmt=" .18f", indent="", newl="\n"):
    a1 = ["{0}{1}".format(indent, arrtostr(row, fmt=fmt, newl="")) for row in a]
    return "{0}{1}{0}{2}".format(newl, newl.join(a1), indent[:-INDENT])

def arrtostr(a, fmt=" .18f", newl="\n", indent=""):
    a1 = " ".join("{0:{1}}".format(x, fmt) for x in a)
    return "{0}{3}{1}{0}{2}".format(newl, a1, indent[:-INDENT], indent)


class VTK:

    @classmethod
    def vtk_cell_types(cls, num_dim, num_node_per_elem):
        return {(2, 3): 5, # VTK_TRIANGLE
                (2, 4): 9, # VTK_QUAD
                (3, 4): 10, # VTK_TETRA
                (3, 8): 12, # VTK_HEXAHEDRON
                (3, 6): 13, # VTK_WEDGE
                (3, 5): 14, # VTK_PYRAMID
                }[(num_dim, num_node_per_elem)]

    def __init__(self, nodes, connect, blocks, sidesets, nodesets):
        num_node, num_dim = nodes.shape
        num_elem, num_node_per_elem = connect.shape
        elem_type = self.vtk_cell_types(num_dim, num_node_per_elem)

        self.doc = xdom.Document()
        root = self.doc.createElementNS("VTK", "VTKFile")
        root.setAttribute("type", "UnstructuredGrid")
        root.setAttribute("version", "0.1")
        root.setAttribute("byte_order", "LittleEndian")
        self.doc.appendChild(root)

        # Unstructured grid element
        usgrid = self.doc.createElementNS("VTK", "UnstructuredGrid")
        root.appendChild(usgrid)

        # Piece 0 (only one)
        piece = self.doc.createElementNS("VTK", "Piece")
        piece.setAttribute("NumberOfPoints", str(num_node))
        piece.setAttribute("NumberOfCells", str(num_elem))
        usgrid.appendChild(piece)

        # Points
        points = self.doc.createElementNS("VTK", "Points")
        piece.appendChild(points)

        # Point location data
        point_coords = self.doc.createElementNS("VTK", "DataArray")
        point_coords.setAttribute("type", "Float32")
        point_coords.setAttribute("format", "ascii")
        point_coords.setAttribute("NumberOfComponents", "3")
        points.appendChild(point_coords)

        if num_dim == 2:
            z = np.zeros(num_node)
            nodes = np.column_stack((nodes, z))
        string = arrtostr2(nodes, indent=10*" ")
        point_coords_data = self.doc.createTextNode(string)
        point_coords.appendChild(point_coords_data)

        # Cells
        cells = self.doc.createElementNS("VTK", "Cells")
        piece.appendChild(cells)

        # Cell connectivity
        cell_connectivity = self.doc.createElementNS("VTK", "DataArray")
        cell_connectivity.setAttribute("type", "Int32")
        cell_connectivity.setAttribute("Name", "connectivity")
        cell_connectivity.setAttribute("format", "ascii")
        cells.appendChild(cell_connectivity)
        string = arrtostr2(connect, "d", indent=10*" ")
        connectivity = self.doc.createTextNode(string)
        cell_connectivity.appendChild(connectivity)

        cell_offsets = self.doc.createElementNS("VTK", "DataArray")
        cell_offsets.setAttribute("type", "Int32")
        cell_offsets.setAttribute("Name", "offsets")
        cell_offsets.setAttribute("format", "ascii")
        cells.appendChild(cell_offsets)
        o = [(i + 1) * num_node_per_elem for i in range(num_elem)]
        string =  arrtostr(o, "d", indent=10*" ")
        offsets = self.doc.createTextNode(string)
        cell_offsets.appendChild(offsets)

        cell_types = self.doc.createElementNS("VTK", "DataArray")
        cell_types.setAttribute("type", "UInt8")
        cell_types.setAttribute("Name", "types")
        cell_types.setAttribute("format", "ascii")
        cells.appendChild(cell_types)
        o = [elem_type for i in range(num_elem)]
        string = arrtostr(o, "d", indent=10*" ")
        types = self.doc.createTextNode(string)
        cell_types.appendChild(types)

        fd = self.doc.createElementNS("VTK", "FieldData")
        root.appendChild(fd)

        for block in blocks:
            name = "ElementBlock_{0}".format(block.id)
            string = arrtostr(block.elements, "d", indent=10*" ")
            blkel = self.doc.createElementNS("VTK", "DataArray")
            blkel.setAttribute("type", "Int32")
            blkel.setAttribute("Name", name)
            blkel.setAttribute("NumberOfTuples", str(len(block.elements)))
            ids = self.doc.createTextNode(string)
            blkel.appendChild(ids)
            fd.appendChild(blkel)

        for sideset in sidesets:
            name = "Sideset_{0}".format(sideset.id)
            string = arrtostr2(sideset.data, "d", indent=10*" ")
            ssel = self.doc.createElementNS("VTK", "DataArray")
            ssel.setAttribute("type", "Int32")
            ssel.setAttribute("Name", name)
            ssel.setAttribute("NumberOfTuples", str(len(sideset.data)*2))
            ids = self.doc.createTextNode(string)
            ssel.appendChild(ids)
            fd.appendChild(ssel)

        for nodeset in nodesets:
            name = "Nodeset_{0}".format(nodeset.id)
            string = arrtostr(nodeset.data, "d", indent=10*" ")
            nsel = self.doc.createElementNS("VTK", "DataArray")
            nsel.setAttribute("type", "Int32")
            nsel.setAttribute("Name", name)
            nsel.setAttribute("NumberOfTuples", str(len(nodeset.data)))
            ids = self.doc.createTextNode(string)
            nsel.appendChild(ids)
            fd.appendChild(nsel)

    def write(self, filename):
        with open(filename, "w") as fh:
            fh.write(self.doc.toprettyxml(indent=" "*INDENT))
        #doc.writexml(open(filename, "w"), indent="  ", newl='\n')


class XML:

    @classmethod
    def cell_types(cls, num_dim, num_node_per_elem):
        return {(2, 3): "TRIANGLE",
                (2, 4): "QUAD",
                (3, 4): "TETRA",
                (3, 8): "HEXAHEDRON",
                (3, 6): "WEDGE",
                (3, 5): "PYRAMID",
                }[(num_dim, num_node_per_elem)]

    def __init__(self, nodes, connect, node_num_map, elem_num_map):
        num_node, num_dim = nodes.shape
        num_elem, num_node_per_elem = connect.shape
        elem_type = self.cell_types(num_dim, num_node_per_elem)

        node_map = dict([(j, i) for (i, j) in node_num_map.items()])
        elem_map = dict([(j, i) for (i, j) in elem_num_map.items()])

        """Write the current mesh to xml"""
        self.doc = xdom.Document()
        mesh = self.doc.createElementNS("XML", "Mesh")
        mesh.setAttribute("version", "1.0")
        self.doc.appendChild(mesh)

        # nodes
        el = self.doc.createElementNS("XML", "Vertices")
        el.setAttribute("dimension", str(num_dim))
        mesh.appendChild(el)
        coords = []
        n = len(str(num_node))
        for (i, node) in enumerate(nodes):
            coords.append(["{0:>{1}d}".format(node_map[i],n)])
            coords[-1].extend(["{0: .18f}".format(x) for x in node[:num_dim]])
        string = arrtostr2(coords, fmt="s", indent=4*" ")
        data = self.doc.createTextNode(string)
        el.appendChild(data)

        # connectivity
        el = self.doc.createElementNS("XML", "Connectivity")
        el.setAttribute("offsets", str(num_node_per_elem))
        el.setAttribute("types", str(elem_type))
        mesh.appendChild(el)
        conn = []
        n = len(str(num_elem))
        for (i, elem) in enumerate(connect):
            conn.append(["{0:>{1}d}".format(elem_map[i],n)])
            conn[-1].extend(["{0:>{1}d}".format(node_map[x],n) for x in elem])
        string = arrtostr2(conn, fmt="s", indent=4*" ")
        data = self.doc.createTextNode(string)
        el.appendChild(data)

    def write(self, filename):
        with open(filename, "w") as fh:
            fh.write(self.doc.toprettyxml(indent=" "*INDENT))

    @classmethod
    def from_mesh(cls, mesh):
        return cls(mesh.coords, mesh.connect, mesh.node_num_map, mesh.elem_num_map)

def meshtovtk(filename):
    mesh = parse_xml(filename)
    vtkfile = splitext(filename)[0] + ".vtu"
    vtkmesh = VTK(mesh.coords, mesh.connect,
                  mesh.blocks, mesh.sidesets, mesh.nodesets)
    vtkmesh.write(vtkfile)

def pvgrid(pvobj, filename):
    """Generate a ParaView source

    This function is not meant to be directly run, but is to be run as a
    ParaView progamable source. In ParaView

    Sources > Programmable Source

    in the properties tab set the Output Data Set to 'vtkUnstructuredGrid' and
    in the script box put

    from mesh.writers import pvgrid
    pvgrid(self, "filename.ext")

    make sure that afepy is on your PYTHONPATH

    """
    from paraview import vtk

    mesh = parse_xml(filename)
    output = pvobj.GetOutput()

    # allocate points
    pts = vtk.vtkPoints()
    for point in mesh.coords:
        if mesh.num_dim == 2:
            point = np.append(point, 0.)
        pts.InsertNextPoint(*point)
    output.SetPoints(pts)

    num_elem, num_node_per_elem = mesh.connect.shape
    output.Allocate(num_elem, 1000)
    for cell in mesh.connect:
        point_ids = vtk.vtkIdList()
        for point_id in range(num_node_per_elem):
            point_ids.InsertId(point_id, int(cell[point_id]))
        cell_type = VTK.vtk_cell_types(mesh.num_dim, num_node_per_elem)
        output.InsertNextCell(cell_type, point_ids)
