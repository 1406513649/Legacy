# Determine platform
if system_is_darwin():
    platform = 'Darwin10.11-x86_64'
else:
    platform = 'rhel6-x86_64'

if True:
    prefix = '/projects/sems/modulefiles'
    if not os.path.isdir(prefix):
        log_error('Load Error: ' + prefix + ' does not exist')
    modulepaths_to_prepend = [os.path.join(prefix, platform, 'sems/utility'),
                              os.path.join(prefix, platform, 'sems/tpl'),
                              os.path.join(prefix, platform, 'sems/compiler')]
else:
    prefix = os.path.join(getenv('MY_MODULEPATH_ROOT'), 'sems', platform)
    if not os.path.isdir(prefix):
        log_error('Load Error: ' + prefix + ' does not exist')
    modulepaths_to_prepend = [os.path.join(prefix, 'core')]

setenv('SEMS_MODULEFILES_ROOT', prefix)
prepend_path('MODULEPATH', *modulepaths_to_prepend)
unload('macports')
