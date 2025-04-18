#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

__version__ = '0.0.1'

requirements = [
    'numpy',
    'scipy',
    'astropy',
    'matplotlib',
    'astroquery',
    'stdpipe',
]

setup(
    name='reticulim',
    version=__version__,
    description='RETICULUM',
    author='Sergey Karpov',
    author_email='karpov.sv@gmail.com',
    url='https://github.com/karpov-sv/reticulum',
    install_requires=requirements,
    packages=['reticulum'],
)
