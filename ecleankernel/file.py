# (c) 2011-2023 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import contextlib
import enum
import errno
import importlib
import logging
import os
import shutil
import struct
import typing

from lzma import LZMADecompressor

from pathlib import Path


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


@contextlib.contextmanager
def autorewind(f: typing.IO[bytes]) -> typing.Iterator[int]:
    """Context manager that autorewinds file to the initial position"""

    offset = f.tell()
    try:
        yield offset
    finally:
        f.seek(offset)


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

    def decompress_raw(self,
                       f: typing.IO[bytes],
                       size: typing.Optional[int] = None,
                       ) -> bytes:
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
        if size and maxlen > size:
            return f.read(size)
        with autorewind(f):
            header = f.read(maxlen)
        buffer = f.read(size or -1)
        for magic, comp in magic_dict.items():
            if header.startswith(magic):
                try:
                    mod = importlib.import_module(comp)
                except ModuleNotFoundError:
                    raise MissingDecompressorError(
                        f'The Python module {comp!r} that is required '
                        f'to decompress kernel file {self.path} '
                        f'is not installed.')
                if comp == 'zstandard':
                    # Technically a redundant import, this is just
                    # to make your IDE happy :)
                    import zstandard
                    decompress = zstandard.ZstdDecompressor().decompressobj()
                    return decompress(buffer)
                elif comp == 'lzma':
                    # Using .decompress() causes an error because of
                    # no end-of-stream marker
                    return LZMADecompressor().decompress(buffer)
                else:
                    return getattr(mod, 'decompress')(buffer)
        return buffer

    def read_internal_version(self) -> str:
        """Read version from the kernel file"""
        with open(self.path, "rb") as f:
            for func in (self.read_version_from_efi,
                         self.read_version_from_bzimage,
                         self.read_version_from_raw,
                         ):
                verbuf = func(f)
                if verbuf is not None:
                    break
            else:
                raise UnrecognizedKernelError(
                    f"Kernel file {self.path} not recognized as any "
                    f"special format and unable to find version string in it")

        ret = verbuf.split(b" ", 1)
        if len(ret) == 1:
            raise UnrecognizedKernelError(
                f"Kernel file {self.path} terminates before end of version "
                "string")
        return ret[0].decode()

    def read_version_from_bzimage(self,
                                  f: typing.IO[bytes],
                                  ) -> typing.Optional[bytes]:
        """Read version from bzImage, if the file is in that format"""

        with autorewind(f):
            f.seek(0x200, 1)
            # short seek would result in eof, so read() will return ''
            buf = f.read(0x10)
            if len(buf) != 0x10 or buf[2:6] != b"HdrS":
                return None

            offset = struct.unpack_from("H", buf, 0x0e)[0]
            f.seek(offset - 0x10, 1)
            buf = f.read(0x100)  # XXX

        if not buf:
            raise UnrecognizedKernelError(
                f"Kernel file {self.path} terminates before expected "
                f"version string position ({offset + 0x200})")
        return buf

    def read_version_from_raw(self,
                              f: typing.IO[bytes],
                              size: typing.Optional[int] = None,
                              ) -> typing.Optional[bytes]:
        """Read version from raw kernel image"""

        # check if it's compressed first
        b = self.decompress_raw(f, size)
        # unlike with bzImage, the raw kernel binary has no header
        # that includes the version, so we parse the version message
        # that appears on boot
        ver_start = 'Linux version '
        pos = b.find(ver_start.encode())
        if pos == -1:
            return None
        pos += len(ver_start)
        sbuf = b[pos:pos + 0x100]
        # Ignore the version information if there are non-ASCII
        # characters at the beginning.
        for byte in sbuf[:4]:
            if byte < 40 or byte > 176:
                return None
        return sbuf

    def read_version_from_efi(self,
                              f: typing.IO[bytes]
                              ) -> typing.Optional[bytes]:
        """Read version from EFI executable image"""

        with autorewind(f) as initial_offset:
            # https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
            # 0x3c is a pointer to the PE format image file
            buf = f.read(0x40)
            if len(buf) != 0x40 or buf[:2] != b"MZ":
                return None

            # handle EFI zboot image
            # see kernel source code
            # drivers/firmware/efi/libstub/zboot-header.S
            if buf[4:8] == b"zimg":
                offset, size = struct.unpack_from("<LL", buf, 8)
                f.seek(offset)
                return self.read_version_from_raw(f, size)

            coff_offset = struct.unpack_from("<L", buf, 0x3c)[0]

            # at offset, we find PE\0\0 signature and COFF file header
            f.seek(coff_offset - 0x40, 1)
            buf = f.read(24)
            if len(buf) != 24 or buf[:4] != b"PE\0\0":
                return None
            _, num_section, _, _, _, opt_header_size, _ = (
                struct.unpack_from("<HHIIIHH", buf, 4))

            # optional part of header follows the "mandatory" part,
            # seek past it
            f.seek(opt_header_size, 1)

            # the header is followed by section table, consisting
            # of [num_section] 40-byte rows
            for i in range(0, num_section):
                buf = f.read(40)
                if len(buf) != 40:
                    raise UnrecognizedKernelError(
                        f"PE file {self.path}: EOF in section table!")
                size = struct.unpack_from("<I", buf, 8)[0]
                offset = struct.unpack_from("<I", buf, 20)[0]
                if buf[:8] == b".uname\0\0":
                    # ukify writes uname -r output into the .uname section
                    # https://uapi-group.org/specifications/specs/unified_kernel_image/
                    f.seek(initial_offset + offset)
                    # the ' (ukify)' suffix is a hack to avoid raising
                    # an exception in read_internal_version()
                    ver = f.read(size) + b" (ukify)"
                    logging.debug(
                        f"Found version {ver!r} in '.uname' section")
                    return ver
                elif buf[:8] == b".linux\0\0":
                    f.seek(initial_offset + offset)
                    for func in (self.read_version_from_bzimage,
                                 self.read_version_from_raw,
                                 ):
                        verbuf = func(f)
                        if verbuf is not None:
                            logging.debug(
                                f"Found version {verbuf!r} in"
                                f" '.linux' section (generic)")
                            return verbuf
            return None

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
