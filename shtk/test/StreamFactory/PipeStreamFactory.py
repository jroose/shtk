import unittest

from ...StreamFactory import PipeStreamFactory
from ...util import export

from ..test_util import register

__all__ = []

@export
@register()
class TestBuild(unittest.TestCase):
    def runTest(self):
        message = "Hello World!"

        psf = PipeStreamFactory()

        with psf.build(None) as ps:
            ps.writer().write(message)
            ps.close_writer()
            observed = ps.reader().read()
        
        self.assertEqual(message, observed)


