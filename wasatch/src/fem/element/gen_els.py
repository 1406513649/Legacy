import rve
import elements as els

els.DEFAULT_ELEMENTS.update({"RVE": rve.RVE})

def element_class_from_name(name):
    for clsnam, el in els.DEFAULT_ELEMENTS.items():
        if el.name[:3].upper() == name[:3].upper():
            return el

def element_class_from_id(eid):
    for name, el in els.DEFAULT_ELEMENTS.items():
        if el.eid == eid:
            return el

def initialize(eltyp, material):
    el = els.DEFAULT_ELEMENTS.get(eltyp.upper())
    if el is None:
        raise WasatchError("{0}: element type not recognized".format(eltyp))
    return el(material)
