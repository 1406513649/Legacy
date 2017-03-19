#!/usr/bin/env python
import numpy as np

from afepy import *
from meshes import slender_beam_xml
from tools.exomgr import put_nodal_solution

mu = 10000.
nu = 0.
E = 2. * mu * (1. + nu)
mat_props = np.array([E, nu])
RUNID = "shear_locking"

def write_analytic_solution(scale=1.):
    mesh = Mesh(file=slender_beam_xml)
    a = 0.15
    b = 1.
    P = 2 * a * b
    L = 10.
    d = -P * L ** 3 / (2 * E * a ** 3 * b)
    II = b * (2. * a) ** 3 / 12.
    u = np.zeros_like(mesh.coords)
    for (i, x) in enumerate(mesh.coords):
        x1, x2 = x
        x2 -= a
        u[i,0] = P / (2. * E * II) * x1 ** 2 * x2 + \
            nu * P / (6 * E * II) * x2 ** 3 - \
            P / (6 * II * mu) * x2 ** 3 - \
            (P * L ** 2 / (2 * E * II) - P * a ** 2 / (2 * II * mu)) * x2
        u[i,1] = -nu * P / (2 * E * II) * x1 * x2 ** 2 - \
            P / (6 * E * II) * x1 ** 3 + \
            P * L ** 2 / (2 * E * II) * x1 - P * L ** 3/(3 * E * II)
    filename = RUNID + "-analytic" + ".exo"
    put_nodal_solution(filename, 2, mesh.coords, mesh.connect, "QUAD", u)
    return

def filename(elem_type):
    if elem_type == "QE4":
        end = "standard"
    elif elem_type == "QE4IM":
        end = "incompatible-modes"
    return RUNID + "-" + end + ".exo"

def run_simulations():
    for elem_type in ("QE4", "QE4IM"):

        mesh = Mesh(file=slender_beam_xml)

        m = Material(name="Mat-1", model="elastic", parameters=mat_props)
        El = FiniteElement(elem_type, m)

        V = FiniteElementSpace(mesh, {"All-Elements": El})

        bc1 = DirichletBC(V, nodeset="Nodeset-10")
        bc2 = DirichletBC(V, nodeset="Nodeset-20", dofs="X")

        t = NeumannBC(V, sideset="Sideset-10", traction=[0., -1.])

        u = SolutionSpace(V)
        StaticLinearSolve(V, u, [bc1, bc2], [t])

        file =    ExodusIIFile(filename(elem_type))
        file << u

write_analytic_solution()
run_simulations()
