local DEVELOPER = os.getenv('DEVELOPER')
local kmm = pathJoin(DEVELOPER, 'kayenta/hosts/matmodlab2')
if isDir(kmm) then
  setenv('MML_USERENV', pathJoin(kmm, 'mml_userenv.py'))
end
