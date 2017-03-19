family('python')

# Determine platform specific prefix
darwin = system_is_darwin()
if darwin:
    root = '/opt'
else:
    home = getenv('HOME')
    root = os.path.join(home, '.swx')

name = self.name
version = self.version
prefix = os.path.join(root, 'apps', name, version)

if not os.path.isdir(prefix):
    log_error('Load Error: ' + prefix + ' does not exist')

PATH = os.path.join(prefix, 'bin')
if os.path.isdir(PATH):
    prepend_path('PATH', PATH)

filename = os.path.join(prefix, 'lib/python' + version,
                        'site-packages/spyderlib/spyder.py')
if os.path.isfile(filename):
    set_alias('spyder', 'python ' + filename)
