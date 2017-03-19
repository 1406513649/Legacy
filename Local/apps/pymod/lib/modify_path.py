import os

def prepend_path(mode, key, path, shell):
    """Prepend path to variable key"""
    if mode == 'load':
        shell.prepend_path(key, path)
    elif mode == 'unload':
        shell.remove_path_first(key)

def append_path(mode, key, path, shell):
    if mode == 'load':
        shell.append_path(key, path)
    elif mode == 'unload':
        # Fake the remove_path function to actually remove
        shell.remove_path_last(key)

def remove_path(mode, key, path, shell):
    if mode == 'load':
        # Remove path from 'key'
        x = shell.remove_path(key, path)

    elif mode == 'unload':
        return
