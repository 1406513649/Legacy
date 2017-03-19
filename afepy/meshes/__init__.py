"""Module designed so that a mesh file's file path can be accessed by
importing it. For example, if you want to get the path to cylinder_3d.xml for
use in a simulation file, put

from meshes import cylinder_3d_xml

and then use cylinder_3d_xml where you would use the path to the file

"""
from os.path import splitext, basename, dirname, realpath, join
from glob import glob

D = dirname(realpath(__file__))
def genkv(filename):
    root, ext = splitext(basename(filename))
    key = root.replace(".", "_")
    if not key.endswith("_xml"):
        key += "_xml"
    val = realpath(join(D, filename))
    return key, val

# put file path to all mesh files in globals so they can be imported
files = glob(join(D, "*.xml.gz")) + glob(join(D, "*.xml"))
globals().update(dict([genkv(f) for f in files]))
