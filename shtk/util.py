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

@export
class Pipe:
    """
    Uses os.pipe2() to create a context manager for an inter-process
    communication pipe.  The underlying pipe gets created when __enter__() is
    called and gets destroyed when __exit__() is called.

    Args:
        flags (int): Flags passed to os.pipe2()
        binary (bool): Indicates whether the file objects should be opened in
            rb/wb (True) or r/w modes.

    Attributes:
        flags (int): Flags passed to os.pipe2()
        binary (bool): Indicates whether the file objects should be opened in
            rb/wb (True) or r/w modes.
        reader (file): Version of the read side of the pipe opened as a file
            object using os.fdopen().
        writer (file): Version of the write side of the pipe opened as a file
            object using os.fdopen().
    """
    def __init__(self, flags = 0, binary=False):
        self.flags = flags
        self.binary = binary
        self.reader = None
        self.writer = None

    def __enter__(self):
        """
        Enters the context manager and creates the pipe

        Returns:
            The Pipe object (self)
        """
        fd_r, fd_w = os.pipe2(self.flags)

        if self.binary:
            self.reader, self.writer = os.fdopen(fd_r, 'rb'), os.fdopen(fd_w, 'wb')
        else:
            self.reader, self.writer = os.fdopen(fd_r, 'r'), os.fdopen(fd_w, 'w')

        return self

    def __exit__(self, exc_type, exc_tb, exc_value):
        """
        Closes the reader and writer (if they're still open).
        """
        self.close()

    def write(self, *args, **kwargs):
        """
        Write to the write side of hte pipe
        """
        return self.writer.write(*args, **kwargs)

    def read(self, *args, **kwargs):
        """
        Read from the read side of the pipe

        Returns:
            Data read from the pipe
        """
        return self.reader.read(*args, **kwargs)

    def close_writer(self):
        """
        Closes the writer, if it's not already closed.
        """
        if not self.writer.closed:
            self.writer.close()

    def close_reader(self):
        """
        Closes the reader, if it's not already closed
        """
        if not self.reader.closed:
            self.reader.close()

    def close(self):
        """
        Closes both the reader and writer if they're not already closed.
        """
        self.close_writer()
        self.close_reader()
