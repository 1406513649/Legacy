#!/usr/bin/env python
from afepy import *
from meshes import mesh_3d_xml
pprecision(2)

mesh = Mesh(file=mesh_3d_xml)
mat = Material(name="Mat-1", model="elastic", parameters=[100., .3])

El = FiniteElement("HEX8", mat)
V = FiniteElementSpace(mesh, {"Block-1": El})

bcs = []
bcs.append(DirichletBC(V, nodeset="Nodeset-1", dofs="XYZ", mag=0.))
bcs.append(DirichletBC(V, nodeset="Nodeset-2", components=(0,-.2,0)))

u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs) #, increments=2, linstiff=True, maxiters=10, period=1., relax=1., tolerance=.0001)
file = ExodusIIFile("single_hex.exo")
file << u
