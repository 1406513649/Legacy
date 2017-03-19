unload('anaconda/3.5')
load('macports')
load('gcc/6.2')
local HOME = os.getenv('HOME')
local prefix = pathJoin(HOME, '.conda/envs/matmodlab')
prepend_path('PATH', pathJoin(prefix, 'bin'))
setenv('CONDA_PREFIX', prefix)
setenv('CONDA_DEFAULT_ENV', 'matmodlab')

local DEVELOPER = os.getenv('DEVELOPER')
mml_userenv = pathJoin(DEVELOPER, 'Kayenta/hosts/matmodlab/mml_userenv.py')
if not isFile(mml_userenv) then
  LmodWarn('Kayenta user environment file not found')
else
  setenv('MML_USERENV', mml_userenv)
end
