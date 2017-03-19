DEVELOPER = getenv('DEVELOPER')
kmm = os.path.join(DEVELOPER, 'kayenta/hosts/matmodlab2')
if os.path.isdir(kmm):
    setenv('MML_USERENV', os.path.join(kmm, 'mml_userenv.py'))
