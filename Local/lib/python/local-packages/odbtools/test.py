import os
from odbhandler import ODBHandler

first = "test/first.odb"
second = "test/second.odb"
third = "test/third.odb"

dest = "test/merged.odb"
if os.path.isfile(dest):
    os.remove(dest)
odb = ODBHandler(first, destination=dest)
odb.merge([second, third])
odb.close()
