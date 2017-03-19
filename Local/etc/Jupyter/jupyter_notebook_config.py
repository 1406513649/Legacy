#--- nbextensions configuration ---
import os
import sys
dot_local = os.getenv('DOT_LOCAL', os.path.expanduser('~/.local.d'))
jupyter_d = os.path.join(dot_local, 'etc/Jupyter')
#ext_d = os.path.join(jupyter_d, 'extensions')
tmpl_d = os.path.join(jupyter_d, 'templates')
assert os.path.isdir(jupyter_d)
#assert os.path.isdir(ext_d)
assert os.path.isdir(tmpl_d)
#sys.path.append(ext_d)
c = get_config()
c.Exporter.template_path = [ '.', tmpl_d ]
#--- nbextensions configuration ---
