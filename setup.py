
PROJECT = 'airena'
VERSION = '0.1'

import os, sys

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages
from distutils.util import convert_path
from fnmatch import fnmatchcase

description = "A platform for experimenting with AI agents"
try:
    long_description = open('README.org', 'rt').read()
except IOError:
    long_description = description

setup(
    name=PROJECT,
    version=VERSION,

    description=description,
    long_description=long_description,

    author='Dustin Lacewell',
    author_email='dlacewell@gmail.com',

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=['distribute', 'argparse', 'pygame', 'straight.plugin'],
    zip_safe=False,

    namespace_packages=[],
    packages=find_packages(),
    # package_data = {
    #     '': ['data/settings.py'],
    # },

    entry_points={
        'console_scripts': [
            'airena = airena.cli:main'
            ],
        'improv.commands': [
            'init = improv.commands.init:Init',
            'apply = improv.commands.apply:Apply',
            ],
        },

    classifiers=['Development Status :: 3 - Alpha',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.2',
                 'Intended Audience :: Developers',
                 'Environment :: Console',
                 ],

    )
