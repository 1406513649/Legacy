#!/usr/bin/env python
from apps.fem import *

model = FEModel(name="mesh_grid_2d-1")

material = model.Material(name="Mat-1", model="elastic",
                          parameters={"E": 100., "NU": .3})

# create mesh
mesh = model.Mesh(type="grid", dimension=2, nx=2, ny=2, lx=1., ly=1.)
block = mesh.ElementBlock(name="Block-1", elements="all")
block.set_properties(elem_type="QE44", material=material)

# node/side sets
mesh.Nodeset(name="NS1", region="JHI")
mesh.Sideset(name="SS1", region="JLO")
mesh.Nodeset(name="NS2", region="JLO")

# fixed nodes
mesh.DisplacementBC(nodeset="NS1")

model.LinearStep(name="Step-1")
#model.steps["Step-1"].DisplacmentBC(nodeset="NS2", dofs="Y", mag=-.01)
#model.steps["Step-1"].Load("CF", nodeset="NS2", dofs="Y", mag=-10.)
model.steps["Step-1"].Load("T", sideset="SS1", components=[0, -100])

model.run()

#if model.solved:
#    model.plot_displacement("y")
#    model.plot_displacement("x")
