# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import enum
import struct

from pathlib import Path


@enum.unique
class KernelFileType(enum.Enum):
    KERNEL = 'vmlinuz'
    SYSTEM_MAP = 'systemmap'
    CONFIG = 'config'
    INITRAMFS = 'initramfs'
    MODULES = 'modules'
    BUILD = 'build'


class UnrecognizedKernelError(Exception):
    pass


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


class KernelImage(GenericFile):
    """A recognized kernel image"""

    internal_version: str

    def __init__(self,
                 path: Path
                 ) -> None:
        super().__init__(path, KernelFileType.KERNEL)
        self.internal_version = self.read_internal_version()

    def read_internal_version(self) -> str:
        """Read version from the kernel file"""
        f = open(self.path, 'rb')
        f.seek(0x200)
        # short seek would result in eof, so read() will return ''
        buf = f.read(0x10)
        if len(buf) != 0x10:
            raise UnrecognizedKernelError(
                f'Kernel file {self.path} terminates before bzImage '
                f'header')
        if buf[2:6] != b'HdrS':
            raise UnrecognizedKernelError(
                f'Unmatched magic for kernel file {self.path} '
                f'({repr(buf[2:6])} != b"HdrS")')
        offset = struct.unpack_from('H', buf, 0x0e)[0]
        f.seek(offset - 0x10, 1)
        buf = f.read(0x100)  # XXX
        if not buf:
            raise UnrecognizedKernelError(
                f'Kernel file {self.path} terminates before expected '
                f'version string position ({offset + 0x200})')
        return buf.split(b' ', 1)[0].decode()
