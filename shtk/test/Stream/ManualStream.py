import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import ManualStream
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestRead(TmpDirMixin):
    def runTest(self):
        message = "Hello World!"
        path = pathlib.Path(self.tmpdir.name).resolve() / "tmp_r.txt"

        with path.open('w') as fout:
            fout.write(message)

        fin = path.open('r')
        stream = ManualStream(fileobj_r=fin)
        reader = stream.reader()
        writer = stream.writer()

        self.assertEqual(reader.read(), message)

        stream.close()

        self.assertFalse(reader.closed)
        #self.assertTrue(writer.closed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        message = "Hello World!"
        path = pathlib.Path(self.tmpdir.name).resolve() / "tmp_w.txt"

        with path.open('w') as fout:
            stream = ManualStream(fileobj_w=fout)
            reader = stream.reader()
            writer = stream.writer()

            self.assertEqual(writer.write(message), len(message))

            stream.close()

            #self.assertTrue(reader.closed)
            self.assertFalse(writer.closed)

        with open(path, 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)
