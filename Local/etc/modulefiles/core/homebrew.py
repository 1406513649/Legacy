## Remove macports
family('package_manager')
remove_path('PATH', '/opt/macports/sbin')
remove_path('PATH', '/opt/macports/bin')

# Add Homebrew
prepend_path('PATH', '/opt/homebrew/sbin')
prepend_path('PATH', '/opt/homebrew/bin')

# Add modules
#LOCAL = getenv('DOT_LOCAL')
#prepend_path('MODULEPATH',
#  os.path.join(DOT_LOCAL, 'etc/modulefiles/software/sw_homebrew/core'))

# Push homebrew to very back
# append_path('/usr/local/sbin')
# append_path('/usr/local/bin')

unsetenv('DYLD_LIBRARY_PATH')
