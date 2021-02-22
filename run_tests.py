#!/usr/bin/env python3
"""Custom test harness for shtk"""

import os
import unittest
import coverage
import pathlib

def main():
    testsdir = pathlib.Path('./shtk/test').resolve()
    packagedir = testsdir.parent

    covdir = pathlib.Path("./coverage").resolve()
    covdir.mkdir(exist_ok=True)

    covhtml = covdir / "html"
    covhtml.mkdir(exist_ok=True)

    covdata = covdir / "datafile"

    print((packagedir / "*").resolve())
    print((testsdir / "*").resolve())

    cov = coverage.Coverage(
        data_file = str(covdata.resolve()),
        include = str((packagedir / "*").resolve()),
        omit = str((testsdir / "*").resolve()),
        config_file = str((testsdir / "coveragerc").resolve())
    )

    cov.start()
    suite = unittest.TestSuite()
    import shtk
    from shtk.test.test_util import test_registry

    for test in test_registry['all']:
        suite.addTest(test())

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
    cov.stop()
    cov.save()
    cov.html_report(directory=str(covhtml))

main()

