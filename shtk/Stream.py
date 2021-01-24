import os
import pathlib

from .util import export

__all__ = []

@export
class Stream:
    def __init__(self, job, fileobj_r=None, fileobj_w=None):
        if fileobj_r is None:
            fileobj_r = open(os.devnull, 'r')

        if fileobj_w is None:
            fileobj_w = open(os.devnull, 'w')
        
        self.fileobj_r = fileobj_r
        self.fileobj_w = fileobj_w

    def reader(self):
        return self.fileobj_r

    def writer(self):
        return self.fileobj_w

    def close_reader(self):
        if self.fileobj_r is not None:
            self.fileobj_r.close()
            self.fileobj_r = None

    def close_writer(self):
        if self.fileobj_w is not None:
            self.fileobj_w.close()
            self.fileobj_w = None

    def close(self):
        self.close_reader()
        self.close_writer()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

@export
class PipeStream(Stream):
    def __init__(self, job, binary=False, flags=0):
        self.pipe_r, self.pipe_w = os.pipe2(os.O_CLOEXEC | flags)
        
        os.set_inheritable(self.pipe_r, True)
        os.set_inheritable(self.pipe_w, True)

        if binary:
            fileobj_r = os.fdopen(self.pipe_r, 'rb')
            fileobj_w = os.fdopen(self.pipe_w, 'wb')
        else:
            fileobj_r = os.fdopen(self.pipe_r, 'r')
            fileobj_w = os.fdopen(self.pipe_w, 'w')

        super().__init__(job, fileobj_r=fileobj_r, fileobj_w=fileobj_w)

@export
class FileStream(Stream):
    def __init__(self, job, partial_path, mode):
        path = pathlib.Path(partial_path)
        if not path.is_absolute():
            path = job.cwd / path
        self.path = path.resolve()

        if 'r' in mode:
            fileobj_r = open(self.path, mode)
        else:
            fileobj_r = None

        if 'w' in mode or 'a' in mode:
            fileobj_w = open(self.path, mode)
        else:
            fileobj_w = None

        super().__init__(job, fileobj_r, fileobj_w)

@export
class NullStream(Stream):
    def __init__(self, job):
        super().__init__(job)

@export
class ManualStream(Stream):
    def __init__(self, job, fileobj_r=None, fileobj_w=None):
        if fileobj_r is None:
            fileobj_r = open(os.devnull, 'r')
            self.close_r = True
        else:
            self.close_r = False

        if fileobj_w is None:
            fileobj_w = open(os.devnull, 'w')
            self.close_w = True
        else:
            self.close_w = False
        
        self.fileobj_r = fileobj_r
        self.fileobj_w = fileobj_w

    def close_reader(self):
        if self.close_r:
            super().close_reader()

    def close_writer(self):
        if self.close_w:
            super().close_writer()
