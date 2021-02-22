"""
A set of common utilities used by other pieces of SHTK.
"""

import pathlib
import os
import os.path
import inspect

__all__ = ["export"]

def export(obj):
    """
    A helpful decorator used to control __all__ in shtk's modules

    Args:
        obj: the object whose name should be added to __all__

    Returns:
        obj

    """
    inspect.getmodule(obj).__all__.append(obj.__name__)
    return obj

@export
def which(name, path=None):
    """
    Searches dirs in path.split(os.pathsep) for an executable file named name

    Args:
        name (str): The name of the program to search for (Default value is
            None, meaning os.environ["PATH"])
        path (str): List of directories to search separated by os.pathsep

    Returns:
        None or pathlib.Path:
            The first found path that meets the requirements or None if a file
            meeting the requirements is not found.

    """
    if path is None:
        path = os.environ['PATH']

    for single_path in path.split(os.pathsep):
        exe_file = pathlib.Path(os.path.expanduser(single_path), name)
        if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
            return exe_file

    return None
