#!/usr/bin/env python
from afepy import *

mesh = Mesh(type="grid", dimension=3, nx=2, ny=2, nz=2, lx=2., ly=2., lz=2.)
mesh.ElementBlock(name="Block-1", elements="all")
mesh.Nodeset(name="Nodeset-1", region="ILO")
mesh.Nodeset(name="Nodeset-2", region="IHI")
mesh.toxml("it.xml")

m = Material(name="Mat-1", model="elastic", parameters={"E": 100., "NU": .3})
El = FiniteElement("HEX8", m)

V = FiniteElementSpace(mesh, {"Block-1": El})

# Initial BCs
bcs = []
bcs.append(DirichletBC(V, nodeset="Nodeset-1", dofs="X"))
bcs.append(DirichletBC(V, nodes=[1], dofs="YZ"))
bcs.append(DirichletBC(V, nodeset="Nodeset-2", dofs="X", mag=.2))

u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, [])

file = ExodusIIFile("mesh_grid_3d.exo")
file << u
