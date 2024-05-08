# (c) 2020 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import abc
import typing


class Bootloader(abc.ABC):
    """A class used to represent a bootloader"""

    name: str

    @abc.abstractmethod
    def __call__(self) -> typing.Iterable[str]:
        """Get list of kernel names known to bootloader"""
        pass

    def has_postrm(self) -> bool:
        """Return True if a meaningful postrm can be run"""
        return False

    def postrm(self) -> None:
        """Perform post-removal tasks"""
        pass


class BootloaderNotFound(Exception):
    pass
