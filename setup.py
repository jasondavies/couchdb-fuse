#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Jason Davies
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name = 'CouchDB-FUSE',
    version = '0.1',
    description = 'CouchDB FUSE module',
    long_description = \
"""This is a Python FUSE module for CouchDB.  It allows CouchDB document
attachments to be mounted on a virtual filesystem and edited directly.""",
    author = 'Jason Davies',
    author_email = 'jason@jasondavies.com',
    license = 'BSD',
    url = 'http://code.google.com/p/couchdb-fuse/',
    zip_safe = True,

    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Database :: Front-Ends',
    ],
    packages = ['couchdbfuse'],

    entry_points = {
        'console_scripts': [
            'couchmount = couchdbfuse:main',
        ],
    },

    install_requires = ['CouchDB>=0.5dev_r123'],
)
