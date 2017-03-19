#!/usr/bin/env python
from afepy import *
from meshes import plane_patch_xml

# Create the mesh
mesh = Mesh(file=plane_patch_xml)
mesh.ElementBlock(name="All", elements="all")
mesh.Sideset(name="RHS", surfaces=[[2, 2], [4, 2]])
mesh.Nodeset(name="FIX-X", nodes=[1, 4, 7], exo_id=10)
mesh.Nodeset(name="FIX-Y", nodes=[1])
mesh.Nodeset(name="RHS", region="IHI")

# Create material and element
mat = Material(name="Mat-1", model="elastic", parameters=[1.0E+03, 2.5E-01])
El = FiniteElement("QE4", mat)

# Finite element space
V = FiniteElementSpace(mesh, {"All": El})

# Boundary condtions
fix_x = DirichletBC(V, nodeset="FIX-X", dofs="X")
fix_y = DirichletBC(V, nodeset="FIX-Y", dofs="Y")
t = NeumannBC(V, sideset="RHS", traction=[1., 0])

bcs = [fix_x, fix_y]

# Solution with linear solver
u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, [t])
file = ExodusIIFile("plane_patch.exo")
file << u.output(node=["stress"])

# Solution with nolinear solver
w = SolutionSpace(V)
StaticNonlinearSolve(V, w, bcs, [t])
file = ExodusIIFile("plane_patch_nl.exo")
file << w.output(node=["stress"])

# Solution with explicit solver
v = SolutionSpace(V)
ExplicitLinearSolve(V, v, bcs, [t], increments=1)
file = ExodusIIFile("plane_patch_dyn.exo")
file << v.output(node=["stress"])
