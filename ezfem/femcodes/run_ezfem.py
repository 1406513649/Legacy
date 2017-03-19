#!/usr/bin/env python
"""Exercise ezfem with 2 element blocks, 1 with quadratic elements and the
other with linear elements.

"""
import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
import ezfem

# Element blocks
elem_blks = {}

im = ezfem.get_mat_by_name("neo-hookean")
dm = ezfem.get_mat_by_name("elastic")

# element block 0: quadratic elements
ql, qn = 1., 1
qe = ezfem.get_elem_by_name("Link3")
qmp = [100.]

# element block 1: linear element
ll, ln = 2., 1
le = ezfem.get_elem_by_name("Link2")
lmp = [100.]

coords, conn, elems = ezfem.genmesh_1d((qn, ql, "quad"), (ln, ll, "linear"),
                                       (qn, ql, "quad"))
func = lambda x: 0

# FE models
elem_blks[0] = (elems[0], qe, im, qmp)
elem_blks[1] = (elems[1], le, im, lmp)
elem_blks[2] = (elems[2], qe, im, qmp)
model_i = ezfem.FEModel(coords, conn, elem_blks, o=0, solver="ite")
model_i.assign_distributed_load(func)
model_i.assign_bc("ilo", "essential", 0.)
model_i.assign_bc("ihi", "natural", 10.)
model_i.solve()

elem_blks[0] = (elems[0], qe, dm, qmp)
elem_blks[1] = (elems[1], le, dm, lmp)
elem_blks[2] = (elems[2], qe, dm, qmp)
model_d = ezfem.FEModel(coords, conn, elem_blks, o=0, solver="dir")
model_d.assign_distributed_load(func)
model_d.assign_bc("ilo", "essential", 0.)
model_d.assign_bc("ihi", "natural", 10.)
model_d.solve()

xi, yi = model_i.interpolated_displacements()
xd, yd = model_d.interpolated_displacements()

plt.plot(xi, yi, label="Iter")
plt.plot(xd, yd, label="Dir")
plt.legend(loc="best")
plt.show()
