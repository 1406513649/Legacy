from setenv import setenv, unsetenv
def family(mode, family_name, module, shell):
    upname = family_name.upper()
    key1 = 'MODULE_FAMILY_{0}'.format(upname)
    key2 = 'MODULE_FAMILY_{0}_VERSION'.format(upname)
    key3 = 'MODULE_FAMILY_{0}_NAME'.format(upname)
    if mode == 'load':
        if key1 in shell.variables:
            # Attempting to load module of same family
            from module_loader import module_loader
            other = shell.variables[key3]
            module_loader('unload', other, shell)
        setenv(mode, key1, module.name, shell)
        setenv(mode, key2, module.version, shell)
        setenv(mode, key3, module.fullname, shell)

    elif mode == 'unload':
        unsetenv(mode, key1, shell)
        unsetenv(mode, key2, shell)
        unsetenv(mode, key3, shell)
