#!/usr/bin/env python
from os.path import join
from apps.fem import *
from meshes import plane_patch_xml

# Create the model
model = FEModel(name="plane_patch_dyn")

# Create the mesh
mesh = model.Mesh(file=plane_patch_xml)

# Create a material
material = model.Material(name="Mat-1", model="elastic",
                          parameters=[1.0E+03, 2.5E-01])

# Create the element block
block = model.ElementBlock(name="All", elements="all", material="Mat-1",
                           elem_type="QE44", density=1.)

# Nodesets and sidesets
model.Sideset(name="RHS", surfaces=[[2, 2], [4, 2]])
model.Nodeset(name="FIX-X", nodes=[1, 4, 7], exo_id=10)
model.Nodeset(name="FIX-Y", nodes=[1])

# Model level (initial) boundary conditions
model.DisplacementBC(nodeset="FIX-X", dofs="X")
model.DisplacementBC(nodeset="FIX-Y", dofs="Y")

# Create an analysis step
step = model.DynamicStep(name="Step-1", solver="linear")

# Create the load
model.Load(step="Step-1", type="T", sideset="RHS", components=[1., 0])

# run the model
model.run()
