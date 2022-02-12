#!/usr/bin/env python
"""
Setup script for SHTK
"""

from setuptools import setup, find_packages
import versioneer

setup(
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    packages=find_packages(include=['shtk'], exclude=['shtk.tests', 'shtk.tests.*'])
)
