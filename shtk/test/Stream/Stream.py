import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import Stream
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestRead(TmpDirMixin):
    def runTest(self):
        message = "Hello World!"
        path = pathlib.Path(self.tmpdir.name) / 'tmp_r.txt'

        with open(path, 'w') as fout:
            fout.write(message)

        fileobj_r = open(path, 'r')
        stream = Stream(fileobj_r=fileobj_r)
        reader = stream.reader()

        self.assertEqual(reader.read(), message)

        stream.close()

        self.assertTrue(reader.closed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        message = "Hello World!"
        path = pathlib.Path(self.tmpdir.name) / 'tmp_r.txt'

        fileobj_w = open(path, 'w')
        stream = Stream(fileobj_w=fileobj_w)
        writer = stream.writer()
        writer.write(message)
        stream.close()
        self.assertTrue(writer.closed)

        with open(path, 'r') as fin:
            self.assertEqual(fin.read(), message)
