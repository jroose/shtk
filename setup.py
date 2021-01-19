#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='ShellToolKit',
    version='1.0',
    description='Shell Toolkit (SHTK)',
    author='Jon Roose',
    author_email='jroose@gmail.com',
    packages=find_packages(include=['shtk', 'shtk.*'])
)
