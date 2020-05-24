# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import abc
import typing

from pathlib import Path

from ecleankernel.file import KernelFileType
from ecleankernel.kernel import Kernel


class Layout(abc.ABC):
    """A class used to represent a /boot layout"""

    name: str

    @staticmethod
    @abc.abstractmethod
    def is_acceptable(root: Path = Path('/')
                      ) -> bool:
        """Return true if this layout is acceptable for `root`"""
        pass

    @abc.abstractmethod
    def find_kernels(self,
                     exclusions: typing.Container[KernelFileType] = [],
                     root: Path = Path('/')
                     ) -> typing.List[Kernel]:
        """
        Find all files and directories related to installed kernels

        Find all kernel files and related data and return a list
        of `Kernel` objects.  `exclusions` specifies kernel parts
        to ignore.  `root` specifies the root directory to use.
        """

        pass
