#!/usr/bin/env python
from afepy import *
raise_e()
from meshes import circ_disc_xml

mesh = Mesh(file=circ_disc_xml)

mat = Material(name="Mat-1", model="elastic", parameters=[1.0E+03, 2.5E-01])
El = FiniteElement("QE4", mat)

V = FiniteElementSpace(mesh, {"Block-1": El})

bcs = []
bcs.append(DirichletBC(V, nodeset="Nodeset-1", dofs="X"))
bcs.append(DirichletBC(V, nodeset="Nodeset-2", dofs="Y"))
f = PointSource(V, nodeset="Nodeset-1", dofs="Y", mag=-5.)

u = SolutionSpace(V)
#StaticLinearSolve(V, u, bcs, [], f)
StaticNonlinearSolve(V, u, bcs, [], f)

file = ExodusIIFile("quarter_circ.exo")
file << u
