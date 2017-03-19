from os.path import splitext
from tools.errors import AFEPYError
from tools.misc import getopt, Int, Float, Array
from mesh import MeshBase

def Mesh(*args, **kwargs):

    filename = kwargs.pop("file", None)
    mesh_type = kwargs.pop("type", None)
    string = kwargs.pop("string", None)

    if all([x is None for x in (filename, mesh_type, string)]):
        raise AFEPYError("Mesh requires 1 of 'filename, type, string' keywords")

    if filename is not None:
        if "xml" in filename.split("."):
            mesh = MeshBase.from_xml(filename=filename)
        elif splitext(filename)[1] in (".g", ".gen"):
            mesh = MeshBase.from_genesis(filename)
        else:
            raise AFEPYError("unknown mesh file extension '{0}'".format(ext))
    elif string is not None:
        mesh = MeshBase.from_xml(string=string)
    else:
        if mesh_type is None:
            raise AFEPYError("grid mesh requires 'type' keyword")

        mt = mesh_type.lower()
        if mt == "grid":
            dim = getopt("dimension", kwargs, pop=1)
            if dim is None:
                raise AFEPYError("grid mesh requires 'dimension' keyword")

            dim = Int(dim)
            if dim not in (2, 3):
                raise AFEPYError("grid mesh requires dim to be 2 or 3")
            nx = Int(getopt("nx", kwargs, 2, pop=1))
            ny = Int(getopt("ny", kwargs, 2, pop=1))
            lx = Float(getopt("lx", kwargs, 1., pop=1))
            ly = Float(getopt("ly", kwargs, 1., pop=1))
            if dim == 2:
                mesh = MeshBase.mesh_grid_2D(nx, ny, lx, ly)
            else:
                nz = Int(getopt("nz", kwargs, 2, pop=1))
                lz = Float(getopt("lz", kwargs, 1., pop=1))
                mesh = MeshBase.mesh_grid_3D(nx, ny, nz, lx, ly, lz, **kwargs)

        elif mt[:5] == "unstr":
            offset = int(getopt("offset", kwargs, 1))
            coords = Array(getopt("vertices", kwargs))
            dim = Int(getopt("dimension", kwargs, coords.shape[1]))
            connect = Array(getopt("connect", kwargs)) - offset
            nmap = getopt("node_num_map", kwargs)
            if nmap is None:
                nmap = dict([(i+1, i) for i in range(coords.shape[0])])
            emap = getopt("elem_num_map", kwargs)
            if emap is None:
                emap = dict([(i+1, i) for i in range(connect.shape[0])])
            mesh = MeshBase(mt, dim, coords, connect, nmap, emap)

        else:
            raise AFEPYError("unknown mesh type '{0}'".format(type))

    return mesh
