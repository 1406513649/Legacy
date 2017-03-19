local HOME = os.getenv('HOME')
local DOT_LOCAL = os.getenv('DOT_LOCAL')
setenv('TRILINOS_ROOT', pathJoin(HOME, 'Development/Trilinos'))
prepend_path('PATH', pathJoin(DOT_LOCAL, 'sw/trilinos/bin'))

unload('anaconda/3.5')
load('anaconda/2.7')
