unload('anaconda/3.5')
load('macports')
load('gcc/6.2')
HOME = getenv('HOME')
prefix = os.path.join(HOME, '.conda/envs/matmodlab')
prepend_path('PATH', os.path.join(prefix, 'bin'))
setenv('CONDA_PREFIX', prefix)
setenv('CONDA_DEFAULT_ENV', 'matmodlab')

DEVELOPER = getenv('DEVELOPER')
mml_userenv = os.path.join(DEVELOPER, 'Kayenta/hosts/matmodlab/mml_userenv.py')
if not os.path.isfile(mml_userenv):
  log_warning('Kayenta user environment file not found')
else:
  setenv('MML_USERENV', mml_userenv)
