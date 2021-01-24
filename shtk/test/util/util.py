import os
import pathlib
import sys
import unittest

from ...util import which, export

from ..test_util import register

__all__ = []

@export
@register()
class TestWhich(unittest.TestCase):
    def runTest(self):
        self.assertIsNotNone(which('sh'))
        self.assertIsNone(which('NAME OF AN EXECUTABLE THAT DOES NOT EXIST'))

