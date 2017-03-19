# This applies to the Apple version numbering
family("compiler")
MY_MODULEPATH_ROOT = getenv("MY_MODULEPATH_ROOT")
MODULEPATH = os.path.join(MY_MODULEPATH_ROOT, "compiler/clang/apple")
prepend_path("MODULEPATH", MODULEPATH)

setenv('CC', 'clang')
setenv('CXX', 'clang++')
setenv('COMPILER', 'clang')
setenv('COMPILER_VER', 'apple')
