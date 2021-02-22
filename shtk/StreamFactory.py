"""
StreamFactory instances are templates that instantiate corresponding instances
of a corresponding Stream class.
"""

import abc
import pathlib

from .Stream import * # pylint: disable=unused-wildcard-import
from .util import export # pylint: disable=unused-import

__all__ = []

@export
class StreamFactory(abc.ABC):
    """
    Base class for templates creating associated Stream instances
    """

    @abc.abstractmethod
    def build(self, job):
        """
        Instantiates the Stream instance

        Args:
            job (Job): job to use for current working directory and environment
                variables.

        Returns:
            Stream:
                The constructed Stream instance.
        """

@export
class PipeStreamFactory(StreamFactory):
    """
    Creates a template for PipeStream instances

    Args:
        flags (int): flags to pass to PipeStream constructor (Default value =
            0).

    Attributes:
        flags (int): flags to pass to PipeStream constructor
    """
    def __init__(self, flags=0):
        super().__init__()
        self.flags = flags

    def build(self, job):
        """
        Instantiates the PipeStream instance

        Args:
            job (Job): job to use for current working directory and environment
                variables.

        Returns:
            PipeStream:
                The constructed PipeStream instance.
        """
        return PipeStream(flags=self.flags)

@export
class FileStreamFactory(StreamFactory):
    """
    Creates a template for FileStream instances

    Args:
        partial_path (str or pathlib.Path): The absolute or job.cwd relative
            path to the file.
        mode (str): The mode to pass to open() when instantiating the
            FileStream.

    Attributes:
        partial_path (pathlib.Path): The absolute or job.cwd relative
            path to the file.
        mode (str): The mode to pass to open() when instantiating the
            FileStream.
    """
    def __init__(self, partial_path, mode):
        super().__init__()
        self.partial_path = pathlib.Path(partial_path)
        self.mode = mode

    def build(self, job):
        """
        Instantiates the FileStream instance

        Args:
            job (Job): job to use for current working directory and environment
                variables.

        Returns:
            FileStream:
                The constructed FileStream instance.
        """

        if self.partial_path.is_absolute():
            return FileStream(self.partial_path, self.mode, user=job.user, group=job.group)
        else:
            return FileStream(
                job.cwd / self.partial_path,
                mode=self.mode,
                user=job.user,
                group=job.group
            )

@export
class NullStreamFactory(StreamFactory):
    """
    Creates a template for NullStream instances
    """
    def build(self, job):
        """
        Instantiates the NullStream instance

        Args:
            job (Job): job to use for current working directory and environment
                variables.

        Returns:
            NullStream:
                The constructed NullStream instance.
        """
        return NullStream()

@export
class ManualStreamFactory(StreamFactory):
    """
    Creates a template for ManualStream instances

    Args:
        fileobj_r (file-like or None): A file-like object suitable for reading.
            None implies os.devnull should be used (Default value = None).
        fileobj_w (file-like or None): A file-like object suitable for writing.
            None implies os.devnull should be used (Default value = None).

    Attributes:
        fileobj_r (file-like or None): A file-like object suitable for reading.
            None implies os.devnull should be used.
        fileobj_w (file-like or None): A file-like object suitable for writing.
            None implies os.devnull should be used.
    """
    def __init__(self, fileobj_r=None, fileobj_w=None):
        self.fileobj_r = fileobj_r
        self.fileobj_w = fileobj_w

    def build(self, job):
        """
        Instantiates the ManualStream instance

        Args:
            job (Job): job to use for current working directory and environment
                variables.

        Returns:
            ManualStream:
                The constructed ManualStream instance.
        """
        return ManualStream(fileobj_r=self.fileobj_r, fileobj_w=self.fileobj_w)
