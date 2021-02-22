import unittest
import pathlib

from ...Job import Job
from ...StreamFactory import FileStreamFactory
from ...util import export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestRead(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = (cwd / "tmp.txt").resolve()
        message = "Hello World!"

        job = Job(None, cwd=cwd)

        with open(tmpfile, 'w') as fout:
            fout.write(message)

        with FileStreamFactory(tmpfile, mode='r').build(job) as fs:
            observed = fs.reader().read()
        
        self.assertEqual(message, observed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = (cwd / "tmp.txt").resolve()
        message = "Hello World!"

        job = Job(None, cwd=cwd)

        with FileStreamFactory(tmpfile, mode='w').build(job) as fs:
            fs.writer().write(message)

        with open(tmpfile, 'r') as fin:
            observed = fin.read()
        
        self.assertEqual(message, observed)

@export
@register()
class TestAppend(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = (cwd / "tmp.txt").resolve()
        message = "Hello World!"

        job = Job(None, cwd=cwd)

        with open(tmpfile, 'w') as fout:
            fout.write(message)

        with FileStreamFactory(tmpfile, mode='a').build(job) as fs:
            fs.writer().write(message)

        with open(tmpfile, 'r') as fin:
            observed = fin.read()
        
        self.assertEqual(message * 2, observed)
