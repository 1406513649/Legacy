# Determine platform
darwin = system_is_darwin()

HOME = getenv('HOME')
DOT_LOCAL = getenv('DOT_LOCAL')
if DOT_LOCAL is None:
  DOT_LOCAL = os.path.join(HOME, '.local.d')
ETC = os.path.join(DOT_LOCAL, 'etc')
SHARE = os.path.join(DOT_LOCAL, 'share')

# Environment variables
setenv('FULLNAME', 'Tim Fuller')
setenv('DEVELOPER', os.path.join(HOME, 'Development'))
setenv('DOCUMENTS', os.path.join(HOME, "Documents"))
setenv('FY', os.path.join(HOME, "FY/Current"))
setenv('PYTHONSTARTUP', os.path.join(ETC, "python/pystartup"))
setenv('ENVIRON', ETC)
setenv('MY_MODULEPATH_ROOT', os.path.join(ETC, "modulefiles"))
setenv('SET_TERM_TITLE_EXE', os.path.join(DOT_LOCAL, "bin/term_title"))
setenv('TEXMFHOME', os.path.join(SHARE, "texmf"))
setenv('CLICOLOR', "1")
setenv('EXINIT', "set flash visualbell showmode noai ic shiftwidth=3")
setenv('COPYFILE_DISABLE', "TRUE")
setenv('MKL_NUM_THREADS', "1")
setenv('HISTCONTROL', "ignoredups:erasedups")
setenv('HISTTIMEFORMAT', "%H:%M > ")
setenv('LESSHISTFILE', "-")
setenv('MYSCRATCH', '/scratch/tjfulle')

if darwin:
    setenv('LSCOLORS', 'Hxfxcxdxcxegedabagacad')
    setenv('UNISON', os.path.join(HOME, 'Library/Unison'))
    setenv('UNISONLOC', os.path.join(HOME, 'Library/Unison'))
    setenv('APPLICATIONS', '/Applications')
    if os.path.isdir(os.path.join(HOME, 'Applications')):
        setenv('MY_APPLICATIONS', os.path.join(HOME, 'Applications'))
    set_alias('cpwd', 'pwd | tr -d "\\n" | pbcopy')
    set_alias('ls', 'ls -F -G')
    texlive = '/usr/local/texlive/2016/bin/x86_64-darwin'
    if os.path.isdir(texlive):
        prepend_path('PATH', texlive)
else:
    setenv('LS_COLORS', 'di=0:fi=0:ln=35:ex=32:pi=5:so=5:bd=5:cd=5:or=31:mi=0')
    set_alias('gsed', 'sed')
    set_alias('ls', 'ls -F --color=auto')
    set_alias('more', 'less')

# Aliases
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
set_shell_function('envgrep', 'env | grep -i --color=auto $1')
set_shell_function('hgrep', 'history | grep -i --color=auto $1')
set_shell_function('psgrep', 'ps -A | grep -i --color=auto $1')
set_shell_function('untar', 'tar -xvf $1')
set_shell_function('untarz', 'tar -xzvf $1')

# Paths
prepend_path('PATH', os.path.join(DOT_LOCAL, 'bin'))
#remove_path('PATH', '/usr/local/bin')
setenv('PYTHONPATH', os.path.join(DOT_LOCAL, 'lib/python/local-packages'))

SWX = os.path.join(HOME, '.swx/bin')
if os.path.isdir(SWX):
    prepend_path('PATH', SWX)

hostname = get_hostname()
if 'sandia' in hostname or 's100' in hostname:
    append_path('PATH', os.path.join(DOT_LOCAL, 'site/snl/bin'))

known = ('ceerws', 'cee-build', 'cee-compute')
if 'ceerws' in hostname or 'cee-build' in hostname or 'cee-compute' in hostname:
    load('snl-proxy')
    append_path('PATH', os.path.join(DOT_LOCAL, 'site/snl/bin'))

if not darwin:
    remove_path('MODULEPATH', '/projects/sems/modulefiles/projects')
    remove_path('MODULEPATH', '/usr/local/modules/3.2.10/Modules/versions')
    remove_path('MODULEPATH', '/usr/local/modules/3.2.10/Modules/$MODULE_VERSION/modulefiles')
    remove_path('MODULEPATH', '/usr/local/modules/3.2.10/Modules/modulefiles')
    remove_path('MODULEPATH', '/usr/share/Modules/modulefiles')
    remove_path('MODULEPATH', '/etc/modulefiles')
