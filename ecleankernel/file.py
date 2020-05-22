# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import enum

from pathlib import Path


@enum.unique
class KernelFileType(enum.Enum):
    KERNEL = 'vmlinuz'
    SYSTEM_MAP = 'systemmap'
    CONFIG = 'config'
    INITRAMFS = 'initramfs'
    MODULES = 'modules'
    BUILD = 'build'


class GenericFile(object):
    """A generic file associated with a kernel"""

    path: Path
    ftype: KernelFileType

    def __init__(self,
                 path: Path,
                 ftype: KernelFileType
                 ) -> None:
        self.path = path
        self.ftype = ftype

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GenericFile):
            return NotImplemented
        return self.path == other.path and self.ftype == other.ftype

    def __repr__(self) -> str:
        return (f'GenericFile({repr(self.path)}, '
                f'KernelFileType.{repr(self.ftype.name)})')
