import asyncio
import os
import pathlib
import sys
import unittest

from ...Stream import NullStream
from ...util import which, export

from ..test_util import register, TmpDirMixin

__all__ = []

@export
@register()
class TestRead(TmpDirMixin):
    def runTest(self):
        stream = NullStream()
        reader = stream.reader()

        message = "Hello World!"
        self.assertEqual(reader.read(), "")

        stream.close()

        self.assertTrue(reader.closed)

@export
@register()
class TestWrite(TmpDirMixin):
    def runTest(self):
        stream = NullStream()
        writer = stream.writer()

        message = "Hello World!"
        self.assertEqual(writer.write(message), len(message))

        stream.close()

        self.assertTrue(writer.closed)
