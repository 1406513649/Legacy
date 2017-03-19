import os
import sys
from odbAccess import openOdb
try:
    filename = sys.argv[1]
except IndexError:
    sys.exit("create_nodesets.py\nusage: create_nodesets <odb file>")
assert os.path.isfile(filename)

odb = openOdb(filename, readOnly=False)

node_labels = range(23)
node_set "foo"

# for instances in an assembly at once
node_labels = (("This-Instance", range(23)), ("That-Instance", range(45, 35)))
odb.rootAssembly.NodeSetFromNodeLabels("node_set_label_1", node_labels)

# for specific instances
label = "node_set_label_2"
node_labels = range(34)
odb.rootAssembly.instances["My-Instance"].NodeSetFromNodeLabels(label, node_labels)

odb.save()
odb.close()

