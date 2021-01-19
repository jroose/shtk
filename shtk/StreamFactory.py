import abc

from .Stream import *
from .util import *

__all__ = []

@export
class StreamFactory(abc.ABC):
    def __init__(self):
        pass

    @abc.abstractmethod
    def build(self, job):
        pass

@export
class PipeStreamFactory(StreamFactory):
    def __init__(self, flags=0):
        super().__init__()
        self.flags = flags

    def build(self, job):
        return PipeStream(job, flags=self.flags)

@export
class FileStreamFactory(StreamFactory):
    def __init__(self, partial_path, mode):
        super().__init__()
        self.partial_path = partial_path
        self.mode = mode

    def build(self, job):
        return FileStream(job, self.partial_path, self.mode)

@export
class NullStreamFactory(StreamFactory):
    def __init__(self, mode):
        self.mode = mode
        
    def build(self, job):
        return NullStream(job, self.mode)

@export
class ShellStreamFactory(StreamFactory):
    def __init__(self, stream_type):
        if stream_type not in ("stdin", "stdout", "stderr"):
            raise ValueError("Argument `stream_type` must be one of stdin, stdout, stderr")
        self.stream_type = stream_type

    def build(self, job):
        return ShellStream(job, self.stream_type)
