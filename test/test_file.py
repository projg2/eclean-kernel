# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import tempfile
import unittest

from pathlib import Path

from ecleankernel.file import KernelImage, UnrecognizedKernelError


def write_bzImage(path: Path,
                  version_line: bytes
                  ) -> None:
    """Write a pseudo-bzImage file at `path`, with `version_line`"""
    with open(path, 'wb') as f:
        f.write(0x202 * b'\0')
        f.write(b'HdrS')
        f.write(8 * b'\0')
        f.write(b'\x10\x00')
        f.write(version_line)


class KernelImageTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.td.cleanup()

    def test_read_internal_version(self):
        path = Path(self.td.name) / 'vmlinuz'
        write_bzImage(path, b'1.2.3 built on test')
        self.assertEqual(
            KernelImage(path).read_internal_version(),
            '1.2.3')

    def test_very_short(self):
        path = Path(self.td.name) / 'vmlinuz'
        with open(path, 'wb') as f:
            f.write(10 * b'\0')
        with self.assertRaises(UnrecognizedKernelError):
            KernelImage(path).read_internal_version()

    def test_bad_magic(self):
        path = Path(self.td.name) / 'vmlinuz'
        with open(path, 'wb') as f:
            f.write(0x210 * b'\0')
        with self.assertRaises(UnrecognizedKernelError):
            KernelImage(path).read_internal_version()

    def test_short(self):
        path = Path(self.td.name) / 'vmlinuz'
        with open(path, 'wb') as f:
            f.write(0x202 * b'\0')
            f.write(b'HdrS')
            f.write(8 * b'\0')
            f.write(b'\x10\x00')
        with self.assertRaises(UnrecognizedKernelError):
            KernelImage(path).read_internal_version()
