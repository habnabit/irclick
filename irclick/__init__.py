# Copyright (c) Aaron Gallagher <_@habnab.it>
# See LICENSE for details.

from ._irclick import line_command, trailer_argument
from ._version import get_versions

__version__ = get_versions()['version']
del get_versions


__all__ = (
    'line_command', 'trailer_argument', '__version__',
)
