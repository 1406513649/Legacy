#!/usr/bin/env python
from afepy import *
verbosity(2)

"""
File: demo.py
Purpose: Demonstrate some capabilities of afepy
      4             3
       o --------- o ->
       |           |
       |     1     |
       |           |
       o --------- o ->
      1             2

"""
#                    DDD  EEEE MM   MM  OOOO     1
#                    D  D E    M M M M O    O  1 1
#                    D  D EEE  M  M  M O    O    1
#                    D  D E    M     M O    O    1
#                    DDD  EEEE M     M  OOOO   11111

# --------------------------------------------------------------------------- #
#                            PRE PROCESSING                                   #
# --------------------------------------------------------------------------- #
# Define the nodes and connectivity of the single element mesh
nodes = array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float64)
connect = array([[1, 2, 3, 4]], dtype=int32)
mesh = Mesh(type="unstructured", dimension=2, vertices=nodes, connect=connect)

# Define an element block on which material properties can be assigned.
# Element blocks are groups of elements of the same type.
mesh.ElementBlock(name="Quad", elements=[1])

# Define the material model, here we use a generic linear elastic model
mat = Material(name="Mat-1", model="elastic", parameters=[96, 1./3.])

# Define an element. QE4FI is a fully integrated 4 node plane-strain
# quadratic element.
E1 = FiniteElement("QE4FI", mat)

# With the mesh and elements created, now create a finite element space on which the problem can be solved.
V = FiniteElementSpace(mesh, {"Quad": E1})

# The second argument to FiniteElementSpace is a dictionary with element block
# name, element type key:value pairs.  Each element block in a mesh should be assigned an element type (otherwise an exception is raised).

# --------------------------------------------------------------------------- #
#                            SOLUTION PHASE
# --------------------------------------------------------------------------- #
# Create the boundary conditons on LHS
bc1 = DirichletBC(V, nodes=[1], dofs="XY")
bc2 = DirichletBC(V, nodes=[4], dofs="X")

# Point forces on RHS
F = PointSource(V, nodes=[2,3], dofs="X", mag=1)

# Define a solution variable
ss = SolutionSpace(V)

# We want to solve K u = F
K = V.stiffness(ss)

# Enforce displacement boundary conditions
V.apply_bcs(ss, [bc1, bc2], K, F)

# --- Solve for the nodal displacement
u = linsolve(K, F)
ss += u

# --------------------------------------------------------------------------- #
#                            POST PROCESSING
# --------------------------------------------------------------------------- #
# Updating stress and strains is a post process
V.update_kinematics(ss, u)
V.update_material(ss, u)

# with the solution now found, we can write it to an exodus file
file = ExodusIIFile("demo_1.exo")
file << ss

#                    DDD  EEEE MM   MM  OOOO    22
#                    D  D E    M M M M O    O  2  2
#                    D  D EEE  M  M  M O    O    2
#                    D  D E    M     M O    O   2
#                    DDD  EEEE M     M  OOOO   22222

# --------------------------------------------------------------------------- #
#                            PRE PROCESSING                                   #
# --------------------------------------------------------------------------- #
s = """
<Mesh>
<Vertices dimension="2">
 1 0 0
 2 1 0
 3 1 1
 4 0 1
</Vertices>
<Connectivity block="Quad" offsets="4">
 1 1 2 3 4
</Connectivity>
</Mesh>
"""
mesh = Mesh(string=s)
mat = Material(name="Mat-1", model="elastic", parameters=[96, 1./3.])
E1 = FiniteElement("QE4FI", mat)
V = FiniteElementSpace(mesh, {"Quad": E1})

# --------------------------------------------------------------------------- #
#                            SOLUTION PHASE
# --------------------------------------------------------------------------- #
bc1 = DirichletBC(V, nodes=[1], dofs="XY")
bc2 = DirichletBC(V, nodes=[4], dofs="X")
F = PointSource(V, nodes=[2,3], dofs="X", mag=1)
u = SolutionSpace(V)
StaticLinearSolve(V, u, [bc1, bc2], F=F)
file = ExodusIIFile("demo_2.exo")
file << u.output(node=["stress", "strain"])

#                    DDD  EEEE MM   MM  OOOO   333
#                    D  D E    M M M M O    O     3
#                    D  D EEE  M  M  M O    O   33
#                    D  D E    M     M O    O     3
#                    DDD  EEEE M     M  OOOO  3333

# --------------------------------------------------------------------------- #
#                            PRE PROCESSING                                   #
# --------------------------------------------------------------------------- #
from meshes import single_quad_xml
mesh = Mesh(file=single_quad_xml)
mat = Material(name="Mat-1", model="elastic", parameters=[96, 1./3.])
E1 = FiniteElement("QE4FI", mat)
V = FiniteElementSpace(mesh, {"Quad": E1})
bc1 = DirichletBC(V, nodes=[1], dofs="XY")
bc2 = DirichletBC(V, nodes=[4], dofs="X")
F = PointSource(V, nodes=[2,3], dofs="X", mag=1)
u = SolutionSpace(V)
StaticNonlinearSolve(V, u, [bc1, bc2], F=F)
file = ExodusIIFile("demo_3.exo")
file << u.output(node=["stress", "strain"])

#                    DDD  EEEE MM   MM  OOOO  4  4
#                    D  D E    M M M M O    O 4  4
#                    D  D EEE  M  M  M O    O 44444
#                    D  D E    M     M O    O    4
#                    DDD  EEEE M     M  OOOO     4

# --------------------------------------------------------------------------- #
#                            PRE PROCESSING                                   #
# --------------------------------------------------------------------------- #
mesh = Mesh(type="grid", dimension=2, nx=2, ny=2, lx=1, ly=1)
mesh.ElementBlock(name="Quad", elements=[1])
mat = Material(name="Mat-1", model="elastic", parameters=[96, 1./3.])
E1 = FiniteElement("QE4FI", mat)
V = FiniteElementSpace(mesh, {"Quad": E1})
bc1 = DirichletBC(V, nodes=[1], dofs="XY")
bc2 = DirichletBC(V, nodes=[3], dofs="X")
F = PointSource(V, nodes=[2,4], dofs="X", mag=1)
u = SolutionSpace(V)
StaticNonlinearSolve(V, u, [bc1, bc2], F=F)
file = ExodusIIFile("demo_4.exo")
file << u.output(node=["stress", "strain"])
