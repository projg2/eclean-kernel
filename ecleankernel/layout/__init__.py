# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import abc
import typing

from pathlib import Path

from ecleankernel.file import KernelFileType
from ecleankernel.kernel import Kernel


class LayoutNotFound(Exception):
    pass


class Layout(abc.ABC):
    """A class used to represent a /boot layout"""

    name: str

    def __init__(self,
                 root: Path = Path('/')
                 ) -> None:
        """
        Instantiate the layout

        Instantiate the layout for specified `root`.  Raise
        LayoutNotFound if the `root` is not suitable for specified
        layout.
        """

        self.root = root

    @abc.abstractmethod
    def find_kernels(self,
                     exclusions: typing.Container[KernelFileType] = [],
                     ) -> typing.List[Kernel]:
        """
        Find all files and directories related to installed kernels

        Find all kernel files and related data and return a list
        of `Kernel` objects.  `exclusions` specifies kernel parts
        to ignore.
        """

        pass
