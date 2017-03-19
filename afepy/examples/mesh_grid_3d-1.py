#!/usr/bin/env python
from afepy import *

material = Material(name="Mat-1", model="elastic", parameters=[100., .3])
mesh = Mesh(type="grid", dimension=3, nx=2, ny=2, nz=2, lx=2., ly=2., lz=2.)
mesh.ElementBlock(name="All-Elements", elements="all")
mesh.Nodeset(name="Nodeset-1", region="JHI")
mesh.Nodeset(name="Nodeset-2", region="JLO")

El = FiniteElement("HEX8", material)

V = FiniteElementSpace(mesh, {"All-Elements": El})
bcs = [DirichletBC(V, nodeset="Nodeset-1"),
       DirichletBC(V, nodeset="Nodeset-2", dofs="Y", mag=-.01)]

u = SolutionSpace(V)
StaticNonlinearSolve(V, u, bcs, increments=1)

file = ExodusIIFile("mesh_grid_3d-1.exo")
file << u
