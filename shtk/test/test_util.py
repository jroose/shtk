"""Helpful tools for creating automated tests"""

import collections
import itertools
import os
import pathlib
import sys
import tempfile
import unittest

from ..util import export

__all__ = ["test_registry"]

test_registry = collections.defaultdict(lambda: [])

@export
def register(*tags):
    """Registers a unit test for the custom test harness"""
    tags = list(tags)
    def register_inner(test_case):
        for tag in itertools.chain(("all",), tags):
            test_registry[tag].append(test_case)
        return test_case
    return register_inner

@export
class TmpDirMixin(unittest.TestCase):
    """Unittest mixin that creates and manages a temporary directory"""
    def setUp(self):
        """Create the temporary directory"""
        super().setUp()
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.__enter__())

    def tearDown(self):
        """Delete the temporary directory"""
        os.chdir(self.old_cwd)
        self.tmpdir.__exit__(None, None, None)
        self.tmpdir.cleanup()
        super().tearDown()
