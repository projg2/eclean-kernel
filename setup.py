#!/usr/bin/python
# vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from setuptools import setup, find_packages

from ecleankernel import __version__

setup(
    name='eclean-kernel',
    version=__version__,
    author='Michał Górny',
    author_email='mgorny@gentoo.org',
    url='http://github.com/mgorny/eclean-kernel',

    packages=find_packages(exclude=['test']),
    scripts=['eclean-kernel'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: System :: Installation/Setup'
    ]
)
