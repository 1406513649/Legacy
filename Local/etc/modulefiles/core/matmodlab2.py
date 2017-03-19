load('anaconda/3.5')

darwin = system_is_darwin()
if darwin:
    load('macports')
else:
    load('sems-env')
    load('gcc/6.1.0')

DEVELOPER = getenv('DEVELOPER')
prefix = os.path.join(DEVELOPER, 'matmodlab2')
prepend_path('PATH', os.path.join(prefix, 'bin'))
setenv('PYTHONPATH', prefix)
