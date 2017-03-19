#!/usr/bin/env python
import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
from ezfem import FEModel

# FE model
num_el = 40
length = 1.
elem_name = "Link3"
mat_name = "elastic"
mat_props = [1.]
model = FEModel.create_uniform(num_el, length, elem_name, mat_name, mat_props,
                               solver="dir")
func = lambda x: -1. * np.sin(x)
model.assign_distributed_load(func)
#model.assign_conc_force(10, -.03)
model.assign_bc("ilo", "essential", 0.)
model.assign_bc("ihi", "essential", 0.)
model.solve()

# Analytic
x = sp.Symbol("x")
u = sp.Function("u")
q = -sp.sin(x)
sol = sp.dsolve(sp.diff(u(x), x, x) + q).rhs
coeffs = sp.solve([sol.subs({x: 0}), sol.subs({x: 1})])
sol = sol.subs(coeffs)
xvals = model.coords
sol = np.array([sol.subs(x, xval).evalf() for xval in xvals])
plt.plot(xvals, sol, "r-")
plt.scatter(model.coords, model.disp)
plt.show()
