import os
import commands
class ShellCommand(object):
    def __init__(self, cmd): self.cmd = cmd
    def __repr__(self): return commands.getstatusoutput(self.cmd)[1]
ls = ShellCommand("ls -la")
pwd = ShellCommand("pwd")
ps = ShellCommand("ps")
