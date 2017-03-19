from numpy import float64, array
from tools.misc import dof_id
from tools.errors import AFEPYError
from bc import BoundaryCondition

class DirichletBC(BoundaryCondition):
    def __init__(self, V=None, mag=None, dofs=None, nodes=None,
                 nodeset=None, region=None, components=None, copy_from=None):
        if copy_from is not None:
            self.data = [x for x in copy_from.data]
        else:
            if V is None:
                raise AFEPYError("missing V")
            node_ids = V.get_node_ids(nodes, nodeset, region)
            components = self.format_components(V, mag, dofs, components)
            self.data = self.init(components, node_ids)

    @staticmethod
    def init(components, node_ids):
        data = []
        for node_id in node_ids:
            for (dof, mag) in enumerate(components):
                if mag is None:
                    continue
                data.append([node_id, dof, mag])
        return data

    @staticmethod
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

    def __iter__(self):
        return iter(self.data)

    def __iadd__(self, other):
        self.data.extend(other.data)
        return self

    def __add__(self, other):
        self.data.extend(other.data)
        return self
