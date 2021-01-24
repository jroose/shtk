import unittest
import pathlib

from ...StreamFactory import ManualStreamFactory
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

        with tmpfile.open('w') as fout:
            fout.write(message)

        with tmpfile.open('r') as fin:
            with ManualStreamFactory(fileobj_r=fin).build(None) as fs:
                observed = fs.reader().read()
        
        self.assertEqual(message, observed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        cwd = pathlib.Path(self.tmpdir.name)
        tmpfile = (cwd / "tmp.txt").resolve()
        message = "Hello World!"

        with tmpfile.open('w') as fout:
            with ManualStreamFactory(fileobj_w=fout).build(None) as fs:
                fs.writer().write(message)

        with tmpfile.open('r') as fin:
            observed = fin.read()
        
        self.assertEqual(message, observed)
