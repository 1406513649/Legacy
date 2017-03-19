#!/usr/bin/env python
import numpy as np

from afepy import *
raise_e()
from meshes import quarter_cylinder_xml, quarter_cylinder_q_xml
from tools.exomgr import put_nodal_solution
import timeit

mu = 1.
nu = .499
E = 2. * mu * (1. + nu)
mat_props = np.array([E, nu])
mat = Material(name="Mat-1", model="elastic", parameters=mat_props)

rootid = "volume_locking"

def write_analytic_solution(scale=1.):
    mesh = Mesh(file=quarter_cylinder_xml)
    a = mesh.coords[0, 1]
    b = mesh.coords[-1, 0]
    p = 1.
    u = np.zeros_like(mesh.coords)
    for (i, x) in enumerate(mesh.coords):
        r = np.sqrt(x[0] ** 2 + x[1] ** 2)
        term1 = (1. + nu) * a ** 2 * b ** 2 * p / (E * (b ** 2 - a ** 2))
        term2 = 1. / r + (1. - 2. * nu) * r / b ** 2
        ur = term1 * term2
        u[i, :] = ur * x[:] / r

    filename = rootid + "-" + "analytic" + ".exo"
    put_nodal_solution(filename, 2, mesh.coords, mesh.connect, "QUAD", u)

    return

def filename(elem_type):
    if elem_type == "QE4":
        end = "bbar"
    if elem_type == "QE4FI":
        end = "full"
    elif elem_type == "QE4RI":
        end = "reduced"
    elif elem_type == "QE4SRI":
        end = "sel-red"
    return rootid + "-" + end + ".exo"

def run_simulations():
    for elem_type in ("QE4", "QE4RI", "QE4FI", "QE4SRI"):

        mesh = Mesh(file=quarter_cylinder_xml)
        mesh.ElementBlock(name="All", elements="all")

        El = FiniteElement(elem_type, mat)

        V = FiniteElementSpace(mesh, {"All": El})
        dx = DirichletBC(mesh, nodeset="Nodeset-10", dofs="X")
        dy = DirichletBC(mesh, nodeset="Nodeset-20", dofs="Y")
        bcs = [dx, dy]

        t1 = NeumannBC(mesh, sideset="Sideset-1",
                       traction=[0.09801714, 0.995184727])
        t2 = NeumannBC(mesh, sideset="Sideset-2",
                       traction=[0.290284677, 0.956940336])
        t3 = NeumannBC(mesh, sideset="Sideset-3",
                       traction=[0.471396737, 0.881921264])
        t4 = NeumannBC(mesh, sideset="Sideset-4",
                       traction=[0.634393284, 0.773010453])
        t5 = NeumannBC(mesh, sideset="Sideset-5",
                       traction=[0.773010453, 0.634393284])
        t6 = NeumannBC(mesh, sideset="Sideset-6",
                       traction=[0.881921264, 0.471396737])
        t7 = NeumannBC(mesh, sideset="Sideset-7",
                       traction=[0.956940336, 0.290284677])
        t8 = NeumannBC(mesh, sideset="Sideset-8",
                       traction=[0.995184727, 0.09801714])
        t = [t1, t2, t3, t4, t5, t6, t7, t8]

        u = SolutionSpace(V)
        StaticLinearSolve(V, u, bcs, t)

        file = ExodusIIFile(filename(elem_type))
        file << u.output(node=("stress", "strain"))

    # quadratic solution
    mesh = Mesh(file=quarter_cylinder_q_xml)
    mesh.ElementBlock(name="All", elements="all")
    El = FiniteElement("QE8FI", mat)
    V = FiniteElementSpace(mesh, {"All": El})
    dx = DirichletBC(V, nodeset="Fix-X", dofs="X")
    dy = DirichletBC(V, nodeset="Fix-Y", dofs="Y")
    bcs = [dx, dy]
    t1 = NeumannBC(V, sideset="Sideset-1", traction=[0.195090322, 0.98078528])
    t2 = NeumannBC(V, sideset="Sideset-2", traction=[0.555570233, 0.831469612])
    t3 = NeumannBC(V, sideset="Sideset-3", traction=[0.831469612, 0.555570233])
    t4 = NeumannBC(V, sideset="Sideset-4", traction=[0.98078528, 0.195090322])
    t = [t1, t2, t3, t4]

    u = SolutionSpace(V)
    StaticLinearSolve(V, u, bcs, t)

    file = ExodusIIFile(rootid + "-quadratic.exo")
    file << u.output(node=("stress", "strain"))

write_analytic_solution()

print timeit.timeit("run_simulations()",
                    setup="from __main__ import run_simulations",
                    number=1)
