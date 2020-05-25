# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import abc
import typing


class Bootloader(abc.ABC):
    """A class used to represent a bootloader"""

    name: str

    @abc.abstractmethod
    def __call__(self) -> typing.Iterable[str]:
        """Get list of kernel names known to bootloader"""
        pass


class BootloaderNotFound(Exception):
    pass
