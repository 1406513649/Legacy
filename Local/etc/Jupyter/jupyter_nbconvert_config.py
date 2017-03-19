#--- nbextensions configuration ---
import os
import sys
jupyter_d = os.path.expanduser('~/Local/env/Jupyter')
ext_d = os.path.join(jupyter_d, 'extensions')
tmpl_d = os.path.join(jupyter_d, 'templates')
assert os.path.isdir(jupyter_d)
assert os.path.isdir(ext_d)
assert os.path.isdir(tmpl_d)
sys.path.append(ext_d)
c = get_config()
c.Exporter.template_path = [ '.', tmpl_d ]
#--- nbextensions configuration ---
