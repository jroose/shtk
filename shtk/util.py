import pathlib
import os
import os.path
import inspect
import contextlib

__all__ =  ["export"]

def export(obj):
    inspect.getmodule(obj).__all__.append(obj.__name__)
    return obj

@export
def which(program):
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    for path in os.environ["PATH"].split(os.pathsep):
        exe_file = pathlib.Path(os.path.expanduser(path), program)
        if is_exe(exe_file):
            return exe_file

    return None

