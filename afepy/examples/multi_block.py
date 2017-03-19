#!/usr/bin/env python
from afepy import *
from meshes import quarter_cylinder_xml

mesh = Mesh(file=quarter_cylinder_xml)
mesh.ElementBlock(name="B1", elements=Range(8))
mesh.ElementBlock(name="B2", elements=Range(8, 16))
mesh.ElementBlock(name="B3", elements=Range(16, 24))
mesh.ElementBlock(name="B4", elements=Range(24, 32))

# set up materials
ET = "QE44"
M1 = Material(name="Mat-1", model="elastic", parameters=[2.998, .499])
E1 = FiniteElement(ET, M1)
M2 = Material(name="Mat-2", model="elastic", parameters=[3.998, .499])
E2 = FiniteElement(ET, M2)
M3 = Material(name="Mat-3", model="elastic", parameters=[4.998, .499])
E3 = FiniteElement(ET, M3)
M4 = Material(name="Mat-4", model="elastic", parameters=[5.998, .499])
E4 = FiniteElement(ET, M4)

V = FiniteElementSpace(mesh, {"B1": E1, "B2": E2, "B3": E3, "B4": E4})


bcs = []
bcs.append(DirichletBC(V, nodeset="Nodeset-10", dofs="X"))
bcs.append(DirichletBC(V, nodeset="Nodeset-20", dofs="Y"))

t = []
t.append(NeumannBC(V, sideset="Sideset-1", traction=[0.09801714, 0.995184727]))
t.append(NeumannBC(V, sideset="Sideset-2", traction=[0.290284677, 0.956940336]))
t.append(NeumannBC(V, sideset="Sideset-3", traction=[0.471396737, 0.881921264]))
t.append(NeumannBC(V, sideset="Sideset-4", traction=[0.634393284, 0.773010453]))
t.append(NeumannBC(V, sideset="Sideset-5", traction=[0.773010453, 0.634393284]))
t.append(NeumannBC(V, sideset="Sideset-6", traction=[0.881921264, 0.471396737]))
t.append(NeumannBC(V, sideset="Sideset-7", traction=[0.956940336, 0.290284677]))
t.append(NeumannBC(V, sideset="Sideset-8", traction=[0.995184727, 0.09801714]))

u = SolutionSpace(V)
StaticLinearSolve(V, u, bcs, t)

file = ExodusIIFile("multi_block.exo")
file << u
