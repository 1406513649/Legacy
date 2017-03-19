import os
from tools.errors import AFEPYError

# Import and add elements to list of elements below
from QE4 import QE4
from QE4FI import QE4FI
from QE4IM import QE4IM
from QE4RI import QE4RI
from QE4SRI import QE4SRI
from QE8FI import QE8FI

from QS4 import QS4

from TRIE3 import TRIE3

from TET4 import TET4

from HEX8 import HEX8
from HEX8RI import HEX8RI
from HEX8SRI import HEX8SRI

els = (QE4, QE4IM, QE4FI, QE4RI, QE4SRI,
       QE8FI, QS4, TRIE3, TET4, HEX8, HEX8RI, HEX8SRI)
ELEMENTS = dict([(el.name.upper(), el) for el in els])

def FiniteElement(elem_type, material, **options):
    """Get the element class for elem_type

    Parameters
    ----------
    elem_type : str
        Element type

    Returns
    -------
    elem_cls : class
        Uninstantiated element class

    """
    try:
        elem_class = ELEMENTS[elem_type.upper()]
    except KeyError:
        raise AFEPYError("{0}: unknown element type".format(elem_type))
    options.update({"density": material.density})
    def Element(elem_id, elem_nodes):
        return elem_class(elem_id, elem_nodes, material, **options)
    return Element
