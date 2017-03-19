from numpy import array
from tools.errors import AFEPYError
from bc import BoundaryCondition

class NeumannBC(BoundaryCondition):
    def __init__(self, V=None, sideset=None, traction=None, copy_from=None):
        """Assign side set tractions"""

        if copy_from is not None:
            self.data = [x for x in copy_from.data]
        else:
            self.data = self._init(V, sideset, traction)

    @staticmethod
    def _init(V, sideset, traction):
        if isinstance(sideset, (tuple, list)):
            sideset = V.Sideset(None, sideset).name

        if sideset not in V.sidesets:
            raise AFEPYError("{0}: invalid side set ID".format(sideset))

        data = []
        for (elem_num, face) in V.sidesets[sideset].surfaces:
            trac = array(traction)[:V.num_dof_per_node]
            data.append([elem_num, face, trac])
        return data

    def __iter__(self):
        return iter(self.data)

    def __iadd__(self, other):
        self.data.extend(other.data)
        return self

    def __add__(self, other):
        self.data.extend(other.data)
        return self
