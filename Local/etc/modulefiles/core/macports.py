# Remove Homebrew
family('package_manager')
remove_path('PATH', '/opt/homebrew/bin')
remove_path('PATH', '/opt/homebrew/sbin')

# Add macports
MACPORTS = '/opt/local'
prepend_path('PATH', os.path.join(MACPORTS, 'sbin'))
prepend_path('PATH', os.path.join(MACPORTS, 'bin'))
setenv('MACPORTS_ROOT', MACPORTS)

# Add modules
HOME = getenv('HOME')
P = getenv('MY_MODULEPATH_ROOT')
prepend_path('MODULEPATH', os.path.join(P, 'macports/core'))

# Push homebrew to very back
# append_path('/usr/local/sbin')
# append_path('/usr/local/bin')

unsetenv('DYLD_LIBRARY_PATH')
