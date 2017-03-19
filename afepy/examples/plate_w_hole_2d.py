#!/usr/bin/env python
from afepy import *
from meshes import plate_w_hole_2d_xml

mesh = Mesh(file=plate_w_hole_2d_xml)

mat = Material(name="Mat-1", model="elastic", parameters=[100., .3])
El = FiniteElement("QE43", mat)

V = FiniteElementSpace(mesh, {"Block-1": El})

bcs = []
bcs.append(DirichletBC(V, nodeset="Nodeset-1", dofs="X"))
bcs.append(DirichletBC(V, nodeset="Nodeset-3"))
bcs.append(DirichletBC(V, nodeset="Nodeset-3", dofs="X", mag=.1))

u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs)

file = ExodusIIFile("plate_w_hole_2d.exo")
file << u
