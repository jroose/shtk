#!/usr/bin/env python
"""
Setup script for SHTK
"""

from setuptools import setup, find_packages

setup(
    name='shtk',
    version='0.9.2',
    description='Shell Toolkit (SHTK)',
    author='Jon Roose',
    author_email='jroose@gmail.com',
    packages=find_packages(include=['shtk'], exclude=['shtk.tests', 'shtk.tests.*'])
)
