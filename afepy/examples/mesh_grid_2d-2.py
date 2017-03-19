#!/usr/bin/env python

from apps.fem import *

model = FEModel("quad")
material = model.Material(name="Mat-1", model="elastic", parameters=[96., 1./3.])

mesh = model.Mesh(type="grid", dimension=2, nx=2, ny=2, lx=2., ly=1.)

block = model.ElementBlock(name="All-Elements", elements="all", material="Mat-1",
                           elem_type="EL2DS4")
model.Nodeset(name="Disp-X", region="IHI")
model.DisplacementBC(nodes=[1])

step = model.StaticStep(name="Step-1")
step.DisplacementBC(nodeset="Disp-X", dofs="X", mag=.1)

model.run()
