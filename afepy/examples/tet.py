#!/usr/bin/env python
from numpy import array, float64, int32
from afepy import *

vertices = array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float64)
connect = array([[1, 2, 3, 4]], dtype=int32)
mesh = Mesh(type="unstructured", vertices=vertices, connect=connect)

# Create material and element
mat = Material(name="Mat-1", model="elastic", parameters=[100, .25])
El = FiniteElement("TET4", mat)

# Finite element space
V = FiniteElementSpace(mesh, {"All": El})

bcs = []
bcs.append(DirichletBC(V, nodes=[1,2,3], dofs="Z"))
bcs.append(DirichletBC(V, nodes=[1], dofs="XY"))
bcs.append(DirichletBC(V, nodes=[4], components=(0,0,.1)))

u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs)

file = ExodusIIFile("tet.exo")
file << u.output(node="stress")
