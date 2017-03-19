family('python')

-- Determine platform specific prefix
local uname = string.lower(capture("uname -a"))
local darwin = uname:find('darwin')
if darwin then
  root = '/opt'
else
  home = os.getenv('HOME')
  root = pathJoin(home, '.swx')
end
local name = myModuleName()
local version = myModuleVersion()
prefix = pathJoin(root, 'apps', name, version)

if (not isDir(prefix)) then
  LmodError('Load Error: ', prefix, 'does not exist')
end

local PATH = pathJoin(prefix, 'bin')
if isDir(PATH) then
  prepend_path('PATH', PATH)
end

local filename = pathJoin(prefix, 'lib/python' .. version,
                          'site-packages/spyderlib/spyder.py')
if isFile(filename) then
  set_alias('spyder', 'python ' .. filename)
end
