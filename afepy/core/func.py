from numpy import ndarray, zeros

class Function(ndarray):
    def __new__(cls, V):
        obj = zeros(V.num_dof).view(cls)
        return obj
