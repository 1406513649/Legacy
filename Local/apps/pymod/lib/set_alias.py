def set_alias(mode, name, value, shell):
    """Set the shell alias"""
    if mode == 'load':
        shell.set_alias(name, value)
    elif mode == 'unload':
        shell.unset_alias(name)

def unset_alias(mode, name, shell):
    """Unset the alias"""
    if mode == 'load':
        shell.unset_alias(name)
    elif mode == 'unload':
        return
