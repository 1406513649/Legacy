-- Remove Homebrew
family('package_manager')
remove_path('PATH', '/opt/homebrew/bin')
remove_path('PATH', '/opt/homebrew/sbin')

-- Add macports
MACPORTS = '/opt/local'
prepend_path('PATH', pathJoin(MACPORTS, 'sbin'))
prepend_path('PATH', pathJoin(MACPORTS, 'bin'))
setenv('MACPORTS_ROOT', MACPORTS)

-- Add modules
HOME = os.getenv('HOME')
P = os.getenv('MY_MODULEPATH_ROOT')
prepend_path('MODULEPATH', pathJoin(P, 'macports/core'))

-- Push homebrew to very back
-- append_path('/usr/local/sbin')
-- append_path('/usr/local/bin')

unsetenv('DYLD_LIBRARY_PATH')
