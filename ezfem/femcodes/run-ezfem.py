#!/usr/bin/env python

"""Script for running the ezfem series of codes

"""

import numpy as np
import matplotlib.pyplot as plt
def plot_disp(*args):
    plt.cla()
    plt.clf()
    for arg in args:
        plt.plot(arg[0], arg[1], label=arg[2])
    plt.legend(loc="best")
    plt.show()

# Problem data
ym = 10.

ebc = [[0, 0, 0.], [1, 0, 1.]]
xcfs = ((.49, 0, 1.),)
end_force = 1.
bf = 0.

num_elem = 5
xa, xb = 0., 1.
ha, hb = 1., 1.
thick = 1.
const_area = 1.
a_xa, a_xb = ha * thick, hb * thick
vari_area = lambda x: a_xa + x / (xb - xa) * (a_xb - a_xa)


res = []

# --- ezfem_0
# This is the first ezfem code
import ezfem_0 as ez0
x_0 = np.linspace(xa, xb, num_elem+1)
y_0 = ez0.uniform_bar(num_elem, xa, xb, end_force, ym, const_area)
t_0 = "ezfem, 0"
res.append((x_0, y_0, t_0))

# --- ezfem_1
import ezfem_1 as ez1
x_1, c_1 = ez1.linmesh_1d(xa, xb, num_elem)
y_1 = ez1.tapered_bar(x_1, c_1, ha, hb, thick, ym, end_force)
t_1 = "ezfem, 1"
res.append((x_1, y_1, t_1))

# --- ezfem_2
import ezfem_2 as ez2
x_2, c_2 = ez2.linmesh_1d(xa, xb, num_elem)
y_2 = ez2.ezfem(x_2, c_2, vari_area, ym, ebc, bf)
t_2 = "ezfem, 2"
res.append((x_2, y_2, t_2))

# --- ezfem_3
import ezfem_3 as ez3
x_3, c_3 = ez3.linmesh_1d(xa, xb, num_elem)
y_3 = ez3.ezfem(x_3, c_3, vari_area, ym, ebc, bf=bf, xcfs=xcfs, enforce=1)
t_3 = "ezfem, 3"
res.append((x_3, y_3, t_3))

# ezfem_4
import ezfem_4 as ez4
x_4, c_4 = ez4.linmesh_1d(xa, xb, num_elem)
y_4 = ez4.ezfem(x_4, c_4, vari_area, ym, ebc, bf=bf, xcfs=xcfs, enforce=1)
t_4 = "ezfem, 4"
res.append((x_4, y_4, t_4))

# --- ezfem_5
import ezfem_5 as ez5
b_5 = (xb, num_elem, "Link2", vari_area, ym)
x_5, c_5, eb_5 = ez5.gen_elem_blks(b_5)
y_5 = ez5.ezfem(x_5, c_5, eb_5, ebc, bf=bf, xcfs=xcfs, enforce=1)
t_5 = "ezfem, 5"
res.append((x_5, y_5, t_5))

# --- ezfem_6
import ezfem_6 as ez6
b_6 = (xb, num_elem, "Link3", vari_area, ym)
x_6, c_6, eb_6 = ez6.gen_elem_blks(b_6)
model = ez6.EzFEM(x_6, c_6, eb_6, ebc, bf=bf, xcfs=xcfs, enforce=1)
model.direct_solve()
y_6 = model.disp
t_6 = "ezfem, 6"
res.append((x_6, y_6, t_6))

# --- ezfem_7
import ezfem_7 as ez7
b_7 = (xb, num_elem, "Link2", vari_area, "elastic", [ym])
x_7, c_7, eb_7 = ez7.gen_elem_blks(b_7)
model = ez7.EzFEM(x_7, c_7, eb_7, ebc, bf=bf, xcfs=xcfs, enforce=1)
model.direct_solve()
y_7 = model.disp
t_7 = "ezfem, 7"
res.append((x_7, y_7, t_7))

# --- ezfem_8
import ezfem_8 as ez8
b_8 = (xb, num_elem, "Link2", vari_area, "elastic", [ym])
x_8, c_8, eb_8 = ez8.gen_elem_blks(b_8)
model = ez8.EzFEM(x_8, c_8, eb_8, ebc, bf=bf, xcfs=xcfs, enforce=1)
model.solve("iter")
y_8 = model.disp
t_8 = "ezfem, 8"
res.append((x_8, y_8, t_8))

# --- ezfem_10
import ezfem_10 as ez10
b_10_a = (xb/2., num_elem/2, "Link2", vari_area, "neohooke", [ym])
b_10_b = (xb/2., num_elem/2, "Link3", vari_area, "elastic", [ym])
mesh = ez10.Mesh1D(b_10_a, b_10_b)

bndry = ez10.Boundary1D()
bndry.assign_bc("essential", "ilo", 0.)
bndry.assign_bc("natural", "ihi", 1.)

model = ez10.EzFEM(mesh, bndry, bf=bf, xcfs=xcfs, enforce=1)
model.solve("iter")
x_10 = model.mesh.coords
y_10 = model.disp
t_10 = "ezfem, 10"
res.append((x_10, y_10, t_10))

plot_disp(*res)
