#!/usr/bin/env python
from afepy import *
from meshes import hex_patch_xml

# Create the mesh
mesh = Mesh(file=hex_patch_xml)

# Create material and element
mat = Material(name="Mat-1", model="elastic", parameters=[10**6, .25])
El = FiniteElement("HEX8", mat)

# Finite element space
V = FiniteElementSpace(mesh, {"All": El})

# Boundary condtions
bcs = []
bcs.append(DirichletBC(V, nodes=[1,2,3,4], dofs="Z"))
bcs.append(DirichletBC(V, nodes=[1], dofs="XY"))
bcs.append(DirichletBC(V, nodes=[5,6,7,8], dofs="Z", mag=.02))

# Solution with linear solver
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs)
file = ExodusIIFile("hex.exo")
file << u.output(node=["stress"])

mesh = Mesh(type="grid", dimension=3, nx=3, ny=3, nz=3,
            lx=1., ly=1., lz=1., center=(.5, .5, .5))
mesh.ElementBlock(name="All", elements="all")
V = FiniteElementSpace(mesh, {"All": El})

# Boundary condtions
bcs = []
bcs.append(DirichletBC(V, region="KLO", dofs="Z"))
bcs.append(DirichletBC(V, nodes=[1], dofs="XY"))
bcs.append(DirichletBC(V, region="KHI", dofs="Z", mag=.02))

# Solution with linear solver
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs)
file = ExodusIIFile("hex-1.exo")
file << u.output(node=["stress"])
