#!/usr/bin/env python
from afepy import *
from meshes import brazilian_xml

# Create the mesh and designate node sets
mesh = Mesh(file=brazilian_xml)
mesh.Nodeset(name="Fix-X", region="ILO")
mesh.Nodeset(name="Fix-Y", region="JLO")
mesh.Nodeset(name="Point-Load", region="X == 0 && y == 75", tol=5.e-03)

# Create material and element
mat = Material(name="Mat-1", model="elastic", parameters=[2000, .4])
El = FiniteElement("TRIE3", mat)

# Finite element space
V = FiniteElementSpace(mesh, {"All": El})

# Essential boundary conditions
bcs = [DirichletBC(V, nodeset="Fix-X", dofs="X"),
       DirichletBC(V, nodeset="Fix-Y", dofs="Y")]

# Point loads
F = PointSource(V, nodeset="Point-Load", components=[0, -1000])

# Solution with linear solver
u = SolutionSpace(V)
#StaticLinearSolve(V, u, bcs, [], F)
StaticNonlinearSolve(V, u, bcs, [], F)
file = ExodusIIFile("brazilian.exo")
file << u.output(node=["stress", "strain"])
