#!/usr/bin/env python
from afepy import *
from meshes import circ_in_square_small_xml

mesh = Mesh(file=circ_in_square_small_xml)
mesh.Nodeset(name="NS1", region="ILO")
mesh.Nodeset(name="NS2", region="IHI")
mesh.Nodeset(name="NS3", region="JLO")
mesh.ElementBlock(name="B1", elements="ALL")

material = Material(name="Mat-1", model="elastic", parameters=[6.8E+10,.33333])
El = FiniteElement("TRIE3", material)

V = FiniteElementSpace(mesh, {"B1": El})

bcs = [DirichletBC(V, nodeset="NS1", dofs="X"),
       DirichletBC(V, nodeset="NS3", dofs="Y"),
       DirichletBC(V, nodeset="NS2", dofs="X", mag=.1)]

u = SolutionSpace(V)
StaticNonlinearSolve(V, u, bcs, period=5.)

file = ExodusIIFile("circle_in_plate.exo")
file << u
