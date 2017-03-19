#!/usr/bin/env python
from afepy import *
from meshes import cylinder_3d_xml

# Create the mesh
mesh = Mesh(file=cylinder_3d_xml)
mesh.ElementBlock(name="All", elements="all")
mesh.Nodeset(name="Fix-X", region="X==0.")
mesh.Nodeset(name="Fix-YZ", nodes=[54])
mesh.Nodeset(name="Disp", region="IHI")
#mesh.Nodeset(name="Fix-YZ", region="X==0 && Y==0 && Z==0", tol=5.E-03)

# Create a material and element
material = Material(name="Mat-1", model="elastic", parameters=[1.0E+03, 2.5E-01])
El = FiniteElement("TET4", material)

# Create the model
V = FiniteElementSpace(mesh, {"All": El})

# Model level (initial) boundary conditions
bc1 = DirichletBC(V, nodeset="Fix-X", dofs="X")
bc2 = DirichletBC(V, nodeset="Fix-YZ", dofs="YZ")
bc3 = DirichletBC(V, nodeset="Disp", dofs="X", mag=.01)
bcs = [bc1, bc2, bc3]

# Create an analysis step
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, [])

file = ExodusIIFile("cylinder_3d.exo")
file << u.output(node="stress")
