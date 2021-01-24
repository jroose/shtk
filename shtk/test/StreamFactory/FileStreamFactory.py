import unittest
import pathlib

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

        with open(tmpfile, 'w') as fout:
            fout.write(message)

        with FileStreamFactory(tmpfile, mode='r').build(None) as fs:
            observed = fs.reader().read()
        
        self.assertEqual(message, observed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = (cwd / "tmp.txt").resolve()
        message = "Hello World!"

        with FileStreamFactory(tmpfile, mode='w').build(None) as fs:
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

        with open(tmpfile, 'w') as fout:
            fout.write(message)

        with FileStreamFactory(tmpfile, mode='a').build(None) as fs:
            fs.writer().write(message)

        with open(tmpfile, 'r') as fin:
            observed = fin.read()
        
        self.assertEqual(message * 2, observed)
