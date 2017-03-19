#!/usr/bin/env python
from afepy import *
from meshes import patch_test_3_xml

# Create the mesh
mesh = Mesh(file=patch_test_3_xml)
mesh.ElementBlock(name="All", elements="all")

# Create material and element
material = Material(name="Mat-1", model="elastic", parameters=[1.0E+06, 2.5E-01])
El = FiniteElement("QE43", material)

V = FiniteElementSpace(mesh, {"All": El})

# Boundary conditions
bcs = [DirichletBC(V, nodes=[1])]
bcs.append(DirichletBC(V, nodes=[2], dofs="X", mag=2.4E-04))
bcs.append(DirichletBC(V, nodes=[2], dofs="Y", mag=1.2E-04))
bcs.append(DirichletBC(V, nodes=[3], dofs="X", mag=3.0E-04))
bcs.append(DirichletBC(V, nodes=[3], dofs="Y", mag=2.4E-04))
bcs.append(DirichletBC(V, nodes=[4], dofs="X", mag=6.0E-05))
bcs.append(DirichletBC(V, nodes=[4], dofs="Y", mag=1.2E-04))

# Solve
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, [])

file = ExodusIIFile("patch_test_3.exo")
file << u
