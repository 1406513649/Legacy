-- Determine platform
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')
local platform
if darwin then
  platform = 'Darwin10.11-x86_64'
else
  platform = 'rhel6-x86_64'
end

local prefix = pathJoin(os.getenv('MY_MODULEPATH_ROOT'), 'sems', platform)
if not isDir(prefix) then
  LmodError('Load Error: ' .. prefix .. ' does not exist')
end
prepend_path('MODULEPATH', pathJoin(prefix, 'core'))
setenv('SEMS_MODULEFILES_ROOT', prefix)
unload('macports')
