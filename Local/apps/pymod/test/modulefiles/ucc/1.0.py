family('compiler')
name = module_name()
version = module_version()
append_path('MODULEPATH', '/{0}/{1}'.format(name, version))
