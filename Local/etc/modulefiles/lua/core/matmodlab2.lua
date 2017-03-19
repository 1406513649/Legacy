load('anaconda/3.5')
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')
if darwin then
  load('macports')
else
  load('sems-env')
  load('gcc/6.1.0')
end

local DEVELOPER = os.getenv('DEVELOPER')
local prefix = pathJoin(DEVELOPER, 'matmodlab2')
prepend_path('PATH', pathJoin(prefix, 'bin'))
setenv('PYTHONPATH', prefix)
