"""
shtk uses Stream instances to track and manage file-like objects used for
input and output streams of subprocesses.
"""

import os
import pathlib
import grp
import pwd

from .util import export

__all__ = []

@export
class Stream:
    """
    Base class for other Stream classes.

    Wraps file-like objects to couple readers and writers to the same streams
    (where it makes sense) and more tightly control closure of the stream.
    Also functions as a context manager (yielding self) that calls self.close()
    upon exit.

    Args:
        fileobj_r (file-like or None): A file-like object suitable for reading.
        fileobj_w (file-like or None): A file-like object suitable for writing.

    Attributes:
        fileobj_r (file-like or None): A file-like object suitable for reading.
        fileobj_w (file-like or None): A file-like object suitable for writing.
    """
    def __init__(self, fileobj_r=None, fileobj_w=None):
        if fileobj_r is None:
            fileobj_r = open(os.devnull, 'r')

        if fileobj_w is None:
            fileobj_w = open(os.devnull, 'w')

        self.fileobj_r = fileobj_r
        self.fileobj_w = fileobj_w

    def reader(self):
        """
        Returns fileobj_r

        Returns:
            file-like:
                self.fileobj_r
        """
        return self.fileobj_r

    def writer(self):
        """
        Returns fileobj_w

        Returns:
            file-like:
                self.fileobj_w
        """
        return self.fileobj_w

    def close_reader(self):
        """Closes self.fileobj_r if it's not None, then set it to None"""
        if self.fileobj_r is not None:
            self.fileobj_r.close()
            self.fileobj_r = None

    def close_writer(self):
        """Closes self.fileobj_w if it's not None, then set it to None"""
        if self.fileobj_w is not None:
            self.fileobj_w.close()
            self.fileobj_w = None

    def close(self):
        """Calls self.close_reader() and self.close_writer()"""
        self.close_reader()
        self.close_writer()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

@export
class PipeStream(Stream):
    """
    Creates an os.pipe2() suitable for communicating between processes

    Args:
        binary (boolean): Whether the streams should be opened in binary mode
            (Default value = False).
        flags (int): Flags to pass to os.pipe2 in addition to os.O_CLOEXEC
            (Default value = 0).
        user (None, int, str): The user that will own the pipe.  If user is an
            int, the file will be chown'd to the user whose uid=user.  If user
            is an str, the file will be chown'd to the user whose name=user.
        group (None, int, str): The group that will own the pipe.  If group is
            an int, the file will be chown'd to the group whose gid=group.  If
            group is an str, the file will be chown'd to the group whose
            name=group.
    """
    def __init__(self, binary=False, flags=0, user=None, group=None):
        self.pipe_r, self.pipe_w = os.pipe2(os.O_CLOEXEC | flags)

        os.set_inheritable(self.pipe_r, True)
        os.set_inheritable(self.pipe_w, True)

        if binary:
            fileobj_r = os.fdopen(self.pipe_r, 'rb')
            fileobj_w = os.fdopen(self.pipe_w, 'wb')
        else:
            fileobj_r = os.fdopen(self.pipe_r, 'r')
            fileobj_w = os.fdopen(self.pipe_w, 'w')

        if user is not None:
            if isinstance(user, str):
                uid = pwd.getpwnam(user).pw_uid
            elif isinstance(user, int):
                uid = user
            else:
                raise ValueError("argument user must be int, str, or none")
        else:
            uid = os.getuid()

        if group is not None:
            if isinstance(group, str):
                gid = grp.getgrnam(group).gr_gid
            elif isinstance(group, int):
                gid = group
            else:
                raise ValueError("argument group must be int, str, or none")
        else:
            gid = os.getgid()

        if user is not None or group is not None:
            os.fchown(self.pipe_r, uid, gid)
            os.fchown(self.pipe_w, uid, gid)

        os.fchmod(self.pipe_r, 0o600)
        os.fchmod(self.pipe_w, 0o600)

        super().__init__(fileobj_r=fileobj_r, fileobj_w=fileobj_w)

@export
class FileStream(Stream):
    """
    Opens a file for reading or writing

    Args:
        path (str or pathlib.Path): The path of the file to open.
        mode (str): Mode passed to open() when opening the file.  If mode
            contains 'r' then the file will be opened for reading.  If the mode
            contains 'w' or 'a' it will be opened for writing.
        user (None, int, str): The user that will own the file (if 'w' in
            mode).  If user is an int, the file will be chown'd to the user
            whose uid=user.  If user is an str, the file will be chown'd to the
            user whose name=user.
        group (None, int, str): The group that will own the file (if 'w' in
            mode).  If group is an int, the file will be chown'd to the group
            whose gid=group.  If group is an str, the file will be chown'd to the
            group whose name=group.
    """
    def __init__(self, path, mode, user=None, group=None):
        self.path = pathlib.Path(path)

        if 'r' in mode:
            fileobj_r = open(self.path.resolve(), mode)
        else:
            fileobj_r = None

        if 'w' in mode or 'a' in mode:
            fileobj_w = open(self.path.resolve(), mode)
        else:
            fileobj_w = None

        if user is not None:
            if isinstance(user, str):
                uid = pwd.getpwnam(user).pw_uid
            elif isinstance(user, int):
                uid = user
            else:
                raise ValueError("argument user must be int, str, or none")
        else:
            uid = os.getuid()

        if group is not None:
            if isinstance(group, str):
                gid = grp.getgrnam(group).gr_gid
            elif isinstance(group, int):
                gid = group
            else:
                raise ValueError("argument group must be int, str, or none")
        else:
            gid = os.getgid()

        if user is not None or group is not None:
            # Only chown the writable files that we create
            if (fileobj_w is not None) and ('w' in mode):
                os.fchown(fileobj_w.fileno(), uid, gid)

        super().__init__(fileobj_r, fileobj_w)

@export
class NullStream(Stream):
    """
    Opens os.devnull for both reading and writing
    """

@export
class ManualStream(Stream):
    """
    Uses provided file-like objects for fileobj_r and fileobj_w.

    Note:
        The files will not be manually closed even when close_reader() or
        close_writer() are called.  Closing the files is the responsibility of
        the caller.

    Args:
        fileobj_r (file-like): The file-like object to use for self.fileobj_r.
        fileobj_w (file-like): The file-like object to use for self.fileobj_w.

    Attributes:
        close_r (boolean): Whether the reader should be closed when
            close_reader() is called.
        close_w (boolean): Whether the writer should be closed when
            close_writer() is called.
    """
    def __init__(self, fileobj_r=None, fileobj_w=None):
        self.close_r = fileobj_r is None
        self.close_w = fileobj_w is None

        super().__init__(fileobj_r=fileobj_r, fileobj_w=fileobj_w)

    def close_reader(self):
        """
        Close the reader only if it wasn't provided at instantiation.
        """
        if self.close_r:
            super().close_reader()

    def close_writer(self):
        """
        Close the writer only if it wasn't provided at instantiation.
        """
        if self.close_w:
            super().close_writer()
