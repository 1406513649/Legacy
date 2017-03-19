# Set environment variable
def setenv(mode, key, val, shell):
    """Set the environment variable, inplace"""
    if mode == 'load':
        shell.setenv(key, val)
    elif mode == 'unload':
        shell.unsetenv(key)

def unsetenv(mode, key, shell):
    """Unset the environment variable, inplace"""
    if mode == 'load':
        shell.unsetenv(key)
    elif mode == 'unload':
        return
