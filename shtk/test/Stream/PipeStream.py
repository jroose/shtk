import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import PipeStream
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestWriteRead(TmpDirMixin):
    def runTest(self):
        expected = "Hello World!"
        ps = PipeStream(None)
        
        writer = ps.writer()
        reader = ps.reader()

        writer.write(expected)

        ps.close_writer()
        self.assertTrue(writer.closed)

        observed = ps.reader().read()
        self.assertEqual(expected, observed)

        ps.close()
        self.assertTrue(reader.closed)
