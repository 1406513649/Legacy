import sys

from utils import system


class ModuleSkipPlatform(Exception):
    pass

def platform(this_platform):
    """Set a platform on which the module is valid"""
    if this_platform.lower() not in system():
        raise ModuleSkipPlatform
