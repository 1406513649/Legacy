-- Determine platform
local uname = string.lower(capture('uname -a'))
local darwin = uname:find('darwin')

local HOME = os.getenv('HOME')
local DOT_LOCAL = os.getenv('DOT_LOCAL')
if DOT_LOCAL == nil then
  DOT_LOCAL = pathJoin(HOME, '.local.d')
end
local ETC = pathJoin(DOT_LOCAL, 'etc')
local SHARE = pathJoin(DOT_LOCAL, 'share')

-- Environment variables
setenv('FULLNAME', 'Tim Fuller')
setenv('DEVELOPER', pathJoin(HOME, 'Development'))
setenv('DOCUMENTS', pathJoin(HOME, "Documents"))
setenv('FY', pathJoin(HOME, "FY/Current"))
setenv('PYTHONSTARTUP', pathJoin(ETC, "python/pystartup"))
setenv('ENVIRON', ETC)
setenv('MY_MODULEPATH_ROOT', pathJoin(ETC, "modulefiles"))
setenv('SET_TERM_TITLE_EXE', pathJoin(DOT_LOCAL, "bin/term_title"))
setenv('TEXMFHOME', pathJoin(SHARE, "texmf"))
setenv('CLICOLOR', "1")
setenv('EXINIT', "set flash visualbell showmode noai ic shiftwidth=3")
setenv('COPYFILE_DISABLE', "TRUE")
setenv('MKL_NUM_THREADS', "1")
setenv('HISTCONTROL', "ignoredups:erasedups")
setenv('HISTTIMEFORMAT', "%H:%M > ")
setenv('LESSHISTFILE', "-")
setenv('MYSCRATCH', '/scratch/tjfulle')

if darwin then
  setenv('LSCOLORS', 'Hxfxcxdxcxegedabagacad')
  setenv('UNISON', pathJoin(HOME, 'Library/Unison'))
  setenv('UNISONLOC', pathJoin(HOME, 'Library/Unison'))
  setenv('APPLICATIONS', '/Applications')
  if isDir(pathJoin(HOME, 'Applications')) then
    setenv('MY_APPLICATIONS', pathJoin(HOME, 'Applications'))
  end
  set_alias('cpwd', 'pwd | tr -d "\\n" | pbcopy')
  set_alias('ls', 'ls -F -G')
  local texlive = '/usr/local/texlive/2016/bin/x86_64-darwin'
  if isDir(texlive) then
    prepend_path('PATH', texlive)
  end
else
  setenv('LS_COLORS', 'di=0:fi=0:ln=35:ex=32:pi=5:so=5:bd=5:cd=5:or=31:mi=0')
  set_alias('gsed', 'sed')
  set_alias('ls', 'ls -F --color=auto')
  set_alias('more', 'less')
end

-- -------------------------------------------------------------------- Aliases
set_alias('functions', 'typeset -F | cut -f 3 -d " "')
set_alias('grep', 'grep -i --color=auto')
set_alias('h', 'history')
set_alias('la', 'ls -a')
set_alias('ll', 'ls -lh')
set_alias('ld', 'ls -ld')
set_alias('lx', 'ls -lXB')
set_alias('lc', 'ls -lcr')
set_alias('lu', 'ls -lur')
set_alias('lr', 'ls -lR')
set_alias('lt', 'ls -ltr')
set_alias('myip', 'ifconfig | grep -m 1 "inet addr"')
set_alias('now', 'date +%Y.%m.%d-%H:%M:%S')
set_alias('today', 'date +%Y%m%d%H%M')
set_alias('whatsize', 'du -kx ~ | sort -n')
set_shell_function('envgrep', 'env | grep -i $@')
set_shell_function('hgrep', 'history | grep -i $@')
set_shell_function('psgrep', 'ps -A | grep -i $@')
set_shell_function('untar', 'tar -xvf $1')
set_shell_function('untarz', 'tar -xzvf $1')

-- ---------------------------------------------------------------------- Paths
prepend_path('PATH', pathJoin(DOT_LOCAL, 'bin'))
--remove_path('PATH', '/usr/local/bin')
setenv('PYTHONPATH', pathJoin(DOT_LOCAL, 'lib/python/local-packages'))

local SWX = pathJoin(HOME, '.swx/bin')
if isDir(SWX) then
  prepend_path('PATH', SWX)
end

local hostname = string.lower(capture('hostname'))
if (hostname:find('sandia')) or (hostname:find('s100')) then
  append_path('PATH', pathJoin(DOT_LOCAL, 'site/snl/bin'))
end
if (hostname:find('ceerws') or hostname:find('cee-build') or
    hostname:find('cee-compute')) then
  load('snl-proxy')
  append_path('PATH', pathJoin(DOT_LOCAL, 'site/snl/bin'))
end

if not darwin then
  remove_path('MODULEPATH', '/projects/sems/modulefiles/projects')
  remove_path('MODULEPATH', '/usr/local/modules/3.2.10/Modules/versions')
  remove_path('MODULEPATH', '/usr/local/modules/3.2.10/Modules/$MODULE_VERSION/modulefiles')
  remove_path('MODULEPATH', '/usr/local/modules/3.2.10/Modules/modulefiles')
  remove_path('MODULEPATH', '/usr/share/Modules/modulefiles')
  remove_path('MODULEPATH', '/etc/modulefiles')
end
