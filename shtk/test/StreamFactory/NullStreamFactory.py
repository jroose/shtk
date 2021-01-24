import unittest
import pathlib

from ...StreamFactory import NullStreamFactory
from ...util import export

from ..test_util import register

__all__ = []

@export
@register()
class TestRead(unittest.TestCase):
    def runTest(self):
        with NullStreamFactory().build(None) as fs:
            observed = fs.reader().read()
        
        self.assertEqual("", observed)

@export
@register()
class TestWrite(unittest.TestCase):
    def runTest(self):
        message = "Hello World!"

        with NullStreamFactory().build(None) as fs:
            fs.writer().write(message)
