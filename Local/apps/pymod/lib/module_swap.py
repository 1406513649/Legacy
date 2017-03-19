from module_loader import module_loader

def module_swap(first, second, mode, shell):
    if mode == 'load':
        module_loader('unload', first, shell)
        module_loader('load', second, shell)
