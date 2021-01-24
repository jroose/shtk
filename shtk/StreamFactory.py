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
    def build(self, job):
        return NullStream(job)

@export
class ManualStreamFactory(StreamFactory):
    def __init__(self, fileobj_r=None, fileobj_w=None):
        self.fileobj_r = fileobj_r
        self.fileobj_w = fileobj_w
            
    def build(self, job):
        return ManualStream(job, fileobj_r=self.fileobj_r, fileobj_w=self.fileobj_w)


