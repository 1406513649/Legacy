def version_control(mode, module, shell):
    """Modules stored as

    name/v1.py  name/v2.py  ...  name/vn.py

    will only be loaded one at a time.

    """
    if mode == 'load':
        other = shell.get_module_by_name(module.name)
        if other is None:
            return
        if other.version == module.version:
            return
        if not other.loaded:
            return
        # Attempting to load module of same name, but different version
        from module_loader import sandbox_run
        sandbox_run('unload', other, shell)
