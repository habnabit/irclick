# Copyright (c) Aaron Gallagher <_@habnab.it>
# See COPYING for details.

from setuptools import setup

import versioneer


setup(
    name='irclick',
    license='Apache 2',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),

    install_requires=['click'],
    packages=['irclick'],
)
