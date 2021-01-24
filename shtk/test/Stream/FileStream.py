import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import FileStream
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestRead(TmpDirMixin):
    def runTest(self):
        message = "Hello World!"
        path = pathlib.Path(self.tmpdir.name).resolve() / "tmp_w.txt"

        with open(path, 'w') as fout:
            fout.write(message)

        stream = FileStream(None, path, mode='r')
        reader = stream.reader()

        self.assertEqual(reader.read(), message)

        stream.close()

        self.assertTrue(reader.closed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        message = "Hello World!"
        path = pathlib.Path(self.tmpdir.name).resolve() / "tmp_w.txt"

        stream = FileStream(None, path, mode='w')
        writer = stream.writer()

        self.assertEqual(writer.write(message), len(message))

        stream.close()

        self.assertTrue(writer.closed)

        with open(path, 'r') as fin:
            observed = fin.read()

        self.assertEqual(message, observed)
