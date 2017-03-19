-- This applies to the Apple version numbering
family("compiler")
local MY_MODULEPATH_ROOT = os.getenv("MY_MODULEPATH_ROOT")
local MODULEPATH = pathJoin(MY_MODULEPATH_ROOT, "compiler/clang/apple")
prepend_path("MODULEPATH", MODULEPATH)

setenv('CC', 'clang')
setenv('CXX', 'clang++')
setenv('COMPILER', 'clang')
setenv('COMPILER_VER', 'apple')
