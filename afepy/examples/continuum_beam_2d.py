#!/usr/bin/env python
from afepy import *
import numpy as np

mu = 10000.
nu = 0.
E = 2. * mu * (1. + nu)
mat_params = np.array([E, nu])
mat = Material(name="Mat-1", model="elastic", parameters=mat_params)

# --------------------------------------------------------------------------- #
mesh = Mesh(type="grid", dimension=2, nx=41, ny=3, lx=20., ly=.5)
mesh.ElementBlock(name="All", elements="all")
mesh.Sideset(name="SS1", region="IHI")
El = FiniteElement("QE4", mat)
V = FiniteElementSpace(mesh, {"All": El})
bcs = [DirichletBC(V, region="ILO")]
t = [NeumannBC(V, sideset="SS1", traction=[0., -1.])]
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, t)
file = ExodusIIFile("continuum_beam_2d.exo")
file << u

# --------------------------------------------------------------------------- #
# same as above, but with incompatible modes element and coarser mesh
mesh = Mesh(type="grid", dimension=2, nx=21, ny=2, lx=20., ly=.5)
mesh.ElementBlock(name="All", elements="all")
mesh.Sideset(name="SS1", region="IHI")
El = FiniteElement("QE4IM", mat)
V = FiniteElementSpace(mesh, {"All": El})
bcs = [DirichletBC(V, region="ILO")]
t = [NeumannBC(V, sideset="SS1", traction=[0., -1.])]
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, t)
file = ExodusIIFile("continuum_beam_2d-incompatible.exo")
file << u

# --------------------------------------------------------------------------- #
# same as above, but with standard element and coarser mesh
El = FiniteElement("QE4", mat)
V = FiniteElementSpace(mesh, {"All": El})
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, t)
file = ExodusIIFile("continuum_beam_2d-incompatible.exo")
file << u
