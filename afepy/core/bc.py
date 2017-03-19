
class BoundaryCondition(object):

    def copy(self):
        return type(self)(copy_from=self)

def bcsum(bcs):
    if not bcs:
        return []
    bc = bcs[0].copy()
    for a in bcs[1:]:
        bc += a
    return bc

