#!/usr/bin/env python
from afepy import *
from meshes import plate_w_hole_3d_xml
pprecision(2)

mat = Material(name="Mat-1", model="elastic", parameters=[100., .3])

mesh = Mesh(file=plate_w_hole_3d_xml)

El = FiniteElement("HEX8", mat)
V = FiniteElementSpace(mesh, {"Block-1": El})

bcs = []
bcs.append(DirichletBC(V, nodeset="Fix-Z", dofs="Z"))
bcs.append(DirichletBC(V, nodeset="Fix-X", dofs="X"))
bcs.append(DirichletBC(V, nodeset="Fix-Y", dofs="Y"))
bcs.append(DirichletBC(V, nodeset="Disp-X", dofs="X", mag=.1))

u = SolutionSpace(V)
StaticNonlinearSolve(V, u, bcs, [])
file = ExodusIIFile("plate_w_hole_3d.exo")
file << u.output(node="stress")

El = FiniteElement("HEX8R", mat)
V = FiniteElementSpace(mesh, {"Block-1": El})
v = SolutionSpace(V)
StaticLinearSolve(V, v, bcs, [])
file = ExodusIIFile("plate_w_hole_3d_reduced.exo")
file << u.output(node="stress")
