#!/usr/bin/env python
from afepy import *

s = """
<Mesh>
<Vertices dimension="2">
 1 1 0
 2 2 0
 3 2 1
 4 1 1
 5 0 0
 6 0 1
 7 .5 .5
</Vertices>
<Connectivity block="Triangles" offsets="3">
 1 5 1 7
 2 1 4 7
 3 7 4 6
 4 5 7 6
</Connectivity>
<Connectivity block="Quad" offsets="4">
 5 1 2 3 4
</Connectivity>
</Mesh>
"""

mesh = Mesh(string=s)

mat = Material(name="Mat-1", model="elastic", parameters=[10, .25])
E1 = FiniteElement("QE4", mat)
E2 = FiniteElement("TRIE3", mat)

V = FiniteElementSpace(mesh, {"Quad": E1, "Triangles": E2})

bcs = []
bcs.append(DirichletBC(V, nodes=[5], dofs="XY"))
bcs.append(DirichletBC(V, nodes=[6], dofs="X"))

t = NeumannBC(V, ((5,2),), traction=[2,0])

f1 = PointSource(V, nodes=[2], components=[1,0])
f2 = PointSource(V, nodes=[3], components=[1,0])
F = f1 + f2

u = SolutionSpace(V)
StaticNonlinearSolve(V, u, bcs, [t])#, F)

file = ExodusIIFile("test.exo")
file << u
