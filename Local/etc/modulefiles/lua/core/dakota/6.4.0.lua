local version = "6.4.0"
local prefix = pathJoin("/opt/apps/dakota", version)
if (not isDir(prefix)) then
        LmodError("Load Error: ", prefix, "directory not found")
end

prereq("compiler", "mpi/openmpi")

local p1 = pathJoin(prefix, "bin")
local p2 = pathJoin(prefix, "lib")
local p3 = pathJoin(prefix, "test")
prepend_path("LD_LIBRARY_PATH", p2)
prepend_path("LD_LIBRARY_PATH", p1)
prepend_path("PATH", p3)
prepend_path("PATH", p1)
