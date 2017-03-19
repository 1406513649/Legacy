from numpy import ndarray, zeros, array, float64
from tools.errors import AFEPYError
from tools.misc import dof_id
from tools.numeric import SparseVector
from bc import BoundaryCondition


class SourceTerm(ndarray):
    def __new__(cls, V, arg=None):
        obj = zeros(V.num_dof).view(cls)
        if arg is not None:
            try:
                data, row = arg
            except:
                raise TypeError('invalid input format')
            obj[row] = data
        return obj

class PointSource(ndarray):
    def __new__(cls, V=None, mag=None, dofs=None, nodes=None,
                 nodeset=None, region=None, components=None):
        node_ids = V.get_node_ids(nodes, nodeset, region)
        components = format_components(V, mag, dofs, components)
        row, data = [], []
        for node_id in node_ids:
            for (dof, mag) in enumerate(components):
                if mag is None:
                    continue
                row.append(int(V.num_dof_per_node * node_id + dof))
                data.append(mag)

        obj = zeros(V.num_dof).view(cls)
        obj[row] = data
        return obj

def format_components(V, mag, dofs, components):
    ndof = V.num_dof_per_node

    if components is not None:
        assert len(components) == ndof
        return array(components, dtype=float64)

    if mag is None:
        mag = 0.

    components = array([None] * ndof)
    if dofs is None:
        dofs = [0, 1, 2][:ndof]
    elif dofs in (0, 1, 2):
        dofs = [dofs,]
    else:
        dofs = [dof_id(dof) for dof in dofs]
    components[dofs] = mag
    return components
