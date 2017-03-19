from module_loader import sandbox_run

def module_purge(shell):
    """Purge all loaded modules"""
    loaded_modules = reversed(shell.loaded_modules())
    for module in loaded_modules:
        sandbox_run('unload', module, shell)

if __name__ == '__main__':
    from shell import Shell
    shell = Shell('bash')
    module_purge(shell)
