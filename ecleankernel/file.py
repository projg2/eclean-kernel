# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import enum
import errno
import importlib
import os
import shutil
import struct
from lzma import LZMADecompressor

from pathlib import Path
from typing import (
    Any,
    BinaryIO,
    Union,
)


@enum.unique
class KernelFileType(enum.Enum):
    KERNEL = 'vmlinuz'
    SYSTEM_MAP = 'systemmap'
    CONFIG = 'config'
    INITRAMFS = 'initramfs'
    MODULES = 'modules'
    BUILD = 'build'
    MISC = 'misc'
    EMPTYDIR = 'emptydir'


class UnrecognizedKernelError(Exception):
    pass


class MissingDecompressorError(Exception):
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

    def remove(self) -> bool:
        """
        Remove this file

        Call an appropriate removal function for this file.  Return True
        if it was successfully removed, False if it was kept.  Raise
        FileNotFoundError if it were not found (which is fine).
        """
        os.unlink(self.path)
        return True

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GenericFile):
            return NotImplemented
        return self.path == other.path and self.ftype == other.ftype

    def __repr__(self) -> str:
        return (f'GenericFile({repr(self.path)}, '
                f'KernelFileType.{repr(self.ftype.name)})')


class GenericDirectory(GenericFile):
    """A subclass of `GenericFile` for directories"""

    def remove(self) -> bool:
        """
        Remove this file

        Call an appropriate removal function for this file.  Return True
        if it was successfully removed, False if it was kept.  Raise
        FileNotFoundError if it were not found (which is fine).
        """
        shutil.rmtree(self.path)
        return True

    def __repr__(self) -> str:
        return (f'GenericDirectory({repr(self.path)}, '
                f'KernelFileType.{repr(self.ftype.name)})')


class KernelImage(GenericFile):
    """A recognized kernel image"""

    internal_version: str

    def __init__(self,
                 path: Path
                 ) -> None:
        super().__init__(path, KernelFileType.KERNEL)
        self.internal_version = self.read_internal_version()

    def ver_from_raw(self, f: BinaryIO) -> Union[str, Any]:
        # unlike with bzImage, the raw kernel binary has no header
        # that includes the version, so we parse the version message
        # that appears on boot
        magic_dict = {
            b'\x1f\x8b\x08': 'gzip',
            b'\x42\x5a\x68': 'bz2',
            b'\xfd\x37\x7a\x58\x5a\x00': 'lzma',
            b'\x5d\x00\x00': 'lzma',
            b'\x04\x22\x4d\x18': 'lz4.frame',
            b'\x28\xb5\x2f\xfd': 'zstandard',
            b'\x89\x4c\x5a\x4f\x00\x0d\x0a\x1a\x0a': 'lzo',
        }
        maxlen = max(len(x) for x in magic_dict)
        f.seek(0)
        header = f.read(maxlen)
        b = None
        for magic, comp in magic_dict.items():
            if header.startswith(magic):
                try:
                    mod = importlib.import_module(comp)
                except ModuleNotFoundError:
                    raise MissingDecompressorError(
                        f'The Python module {comp!r} that is required '
                        f'to decompress kernel file {self.path} '
                        f'is not installed.')

                # Start again from beginning of file
                f.seek(0)

                if comp == 'zstandard':
                    # Technically a redundant import, this is just
                    # to make your IDE happy :)
                    import zstandard
                    reader = zstandard.ZstdDecompressor().stream_reader(f)
                    decomp = b''
                    while True:
                        chunk = reader.read(1024 * 1024)
                        if not chunk:
                            break
                        decomp += chunk
                    return decomp
                elif comp == 'lzma':
                    # Using .decompress() causes an error because of
                    # no end-of-stream marker
                    return LZMADecompressor().decompress(f.read())
                else:
                    b = getattr(mod, 'decompress')(f.read())
        if b is None:
            b = f.read()
        ver_start = 'Linux version '
        pos = b.find(ver_start.encode())
        if pos == -1:
            raise UnrecognizedKernelError(
                f'Kernel file {self.path} does not appear '
                f'to have a version string, '
                f'or the compression format was not recognized')
        pos += len(ver_start)
        sbuf = b[pos:pos + 0x100]
        ret = sbuf.split(b' ', 1)
        if len(ret) == 1:
            raise UnrecognizedKernelError(
                f'Kernel file {self.path} terminates '
                f'before end of version string')
        return ret[0].decode()

    def ver_from_BzImage(self, f: BinaryIO) -> str:
        f.seek(0x200, 1)
        # short seek would result in eof, so read() will return ''
        buf = f.read(0x10)
        if len(buf) != 0x10:
            raise UnrecognizedKernelError(
                f'Kernel file {self.path} terminates before bzImage '
                f'header')
        offset = struct.unpack_from('H', buf, 0x0e)[0]
        f.seek(offset - 0x10, 1)
        buf = f.read(0x100)  # XXX
        if not buf:
            raise UnrecognizedKernelError(
                f'Kernel file {self.path} terminates before expected '
                f'version string position ({offset + 0x200})')
        ret = buf.split(b' ', 1)
        return ret[0].decode()

    def read_internal_version(self) -> str:
        """Read version from the kernel file"""
        f = open(self.path, 'rb')

        if f.read(2) == b'MZ':
            # 0x3c is a pointer to the PE format image file. Find the
            # offset to that file, then seek to it.
            # https://learn.microsoft.com/en-us/windows/win32/debug/pe-format#signature-image-only
            f.seek(0x3c)
            header_pos = struct.unpack('B', f.read(1))[0]
            f.seek(header_pos)

            # Check that the PE file is actually at this offset
            if f.read(4) != b'PE\x00\x00':
                raise UnrecognizedKernelError(
                    f"Kernel file {self.path} does not appear to contain"
                    "expected PE magic signature 'PE'")

            # From here, we're working with a COFF file header
            # formatted according to:
            # https://learn.microsoft.com/en-us/windows/win32/debug/pe-format#coff-file-header-object-and-image
            fields = struct.unpack("HHIIIHH", f.read(20))

            # Most notably, the "number of sections" is the 2nd field,
            # and the "size of optional header" is sixth (starting
            # from 1). Thus:
            numberOfSections = fields[1]
            sizeOfOptionalHeader = fields[5]

            # At this point, we've seeked to the end of the
            # "mandatory" part of the header. There's optional header data at
            # the end of this mandatory header, so we seek to the end
            # of that using the previously retrieved size of it,
            # because we want to look into the sections of the binary
            # that come after the entire header.
            f.seek(sizeOfOptionalHeader, 1)

            # After that, we're finally at the section table, specified here:
            # https://learn.microsoft.com/en-us/windows/win32/debug/pe-format#section-table-section-headers
            # So, iterate through each section, look at its first 8
            # bytes to check for the name ".linux", and if found, grab
            # the pointer to the kernel data at offset 20
            pointerToRawData = 0
            for i in range(0, numberOfSections):
                name = f.read(8).decode('utf-8')
                if name.startswith(".linux"):
                    # Read the pointer (4 bytes) at offset 20, we'll
                    # end up at offset 24
                    f.seek(12, 1)
                    pointerToRawData = struct.unpack('I', f.read(4))[0]

                    # Seek back to the beginning of the header to
                    # continue parsing
                    f.seek(-24, 1)
                    break
                # Jump to the end of the header, at offset 40, from
                # current offset 8 (just after the name field)
                f.seek(32, 1)
            f.seek(pointerToRawData)

            # If the image is still valid, the header magic signature
            # will be at 0x202, according to:
            # https://www.kernel.org/doc/html/latest/x86/boot.html#the-real-mode-kernel-header
            f.seek(0x202, 1)
            if f.read(4) == b'HdrS':
                # And if it was really there, seek back to the
                # beginning of the header and find the kernel version
                # via ver_from_bzImage
                f.seek(-0x206, 1)
                return self.ver_from_BzImage(f)
            else:
                raise UnrecognizedKernelError(
                    f"Kernel file {self.path} does not appear to contain"
                    "expected magic signature 'HdrS'")
        else:
            # If it's not a PE file it must be a raw, compressed image
            return self.ver_from_raw(f)

    def __repr__(self) -> str:
        return (f'KernelImage({repr(self.path)})')


class ModuleDirectory(GenericDirectory):
    """A kernel module collection directory"""

    def __init__(self,
                 path: Path
                 ) -> None:
        super().__init__(path, KernelFileType.MODULES)

    def get_build_dir(self) -> Path:
        return self.path / os.readlink(self.path / 'build')

    def __repr__(self) -> str:
        return (f'ModuleDirectory({repr(self.path)})')


class EmptyDirectory(GenericFile):
    """A parent directory that is removed if it is empty"""

    def __init__(self,
                 path: Path
                 ) -> None:
        super().__init__(path, KernelFileType.EMPTYDIR)

    def remove(self) -> bool:
        try:
            os.rmdir(self.path)
        except OSError as e:
            if e.errno in (errno.EEXIST, errno.ENOTEMPTY):
                return False
            raise
        return True

    def __repr__(self) -> str:
        return (f'EmptyDirectory({repr(self.path)})')
