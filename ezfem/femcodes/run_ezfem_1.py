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

# element block 0: quadratic elements
ql, qn = 1., 2
qe = "Link3"
qm = "elastic"
qmp = [1.]

# element block 1: linear elements
ll, ln = 2., 2
le = "Link2"
lm = "elastic"
lmp = [1.]

# FE model
model = ezfem.FEModel.create_gen((qn, ql, qe, qm, qmp), (ln, ll, le, lm, lmp),
                                 (qn, ql, qe, qm, qmp))

func = lambda x: -10
model.assign_distributed_load(func)
model.assign_bc("ilo", "essential", 0.)
model.assign_bc("ihi", "essential", 0.)
model.solve()
model.plot_disp()
