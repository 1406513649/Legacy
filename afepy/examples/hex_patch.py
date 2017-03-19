#!/usr/bin/env python
from afepy import *
from meshes import hex_patch_1_xml

# Create the mesh
mesh = Mesh(file=hex_patch_1_xml)

# Create material and element
mat = Material(name="Mat-1", model="elastic", parameters=[10**6, .25], density=1000)
El = FiniteElement("HEX8", mat)

# Finite element space
V = FiniteElementSpace(mesh, {"All": El})

# Boundary condtions
fac = 10 ** -3
bcs = []
bcs.append(DirichletBC(V, nodes=[1], components=(0.0*fac, 0.0*fac, 0.0*fac)))
bcs.append(DirichletBC(V, nodes=[2], components=(1.0*fac, 0.5*fac, 0.5*fac)))
bcs.append(DirichletBC(V, nodes=[3], components=(1.5*fac, 1.5*fac, 1.0*fac)))
bcs.append(DirichletBC(V, nodes=[4], components=(0.5*fac, 1.0*fac, 0.5*fac)))
bcs.append(DirichletBC(V, nodes=[5], components=(0.5*fac, 0.5*fac, 1.0*fac)))
bcs.append(DirichletBC(V, nodes=[6], components=(1.5*fac, 1.0*fac, 1.5*fac)))
bcs.append(DirichletBC(V, nodes=[7], components=(2.0*fac, 2.0*fac, 2.0*fac)))
bcs.append(DirichletBC(V, nodes=[8], components=(1.0*fac, 1.5*fac, 1.5*fac)))

#u = SolutionSpace(V)
#ModeShapes(V, u, bcs)
#exit()

# Solution with linear solver
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs)
file = ExodusIIFile("hex_patch.exo")
file << u.output(node=["stress"])
