#!/usr/bin/env python
from apps.fem import *

model = FEModel(name="mesh_grid_2d")
mesh = model.Mesh(type="grid", dimension=2, nx=10, ny=100, lx=10., ly=100.)
material = model.Material(name="Mat-1", model="elastic",
                          parameters={"E": 100., "NU": -.1})

# create element block
block = mesh.ElementBlock(name="Block-1", elements="all")
block.set_properties(elem_type="QE44", material=material)

# node/side sets
mesh.Nodeset(name="Nodeset-1", region="JHI")
mesh.Sideset(name="Sideset-1", region="JLO")
mesh.Nodeset(name="Nodeset-2", region="JLO")

# fixed nodes
model.DisplacementBC(nodeset="Nodeset-1")

step = model.LinearStep(name="Step-1")
step.DisplacementBC(nodeset="Nodeset-2", dofs="Y", mag=-10)
#step.Load(type="CF", sideset="Sideset-1", dofs="Y", -10.)
#step.Load(type="T", sideset="Sideset-1", components=[0, -10])

model.run()

if model.solved and False:
    model.plot_displacement("y")
    model.plot_displacement("x")
