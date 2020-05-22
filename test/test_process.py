# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from ecleankernel.file import KernelFileType, GenericFile, KernelImage
from ecleankernel.kernel import Kernel
from ecleankernel.process import (
    RemovableKernelFiles,
    get_removable_files,
    get_removal_list,
    remove_stray,
    )

from test.test_file import write_bzImage


class KernelRemovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kernels = [
            Kernel('old'),
            Kernel('new'),
            Kernel('stray'),
            Kernel('stray-files'),
        ]

        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        write_bzImage(td / 'kernel.old', b'old')
        write_bzImage(td / 'kernel.new', b'new')
        new_stat = os.stat(td / 'kernel.new')
        # make sure that 'new' is newer
        os.utime(td / 'kernel.old', (new_stat.st_atime,
                                     new_stat.st_mtime - 1))
        with open(td / 'config-stray', 'w'):
            pass
        with open(td / 'initrd-stray.img', 'w'):
            pass
        os.mkdir(td / 'build')

        build = GenericFile(td / 'build', KernelFileType.BUILD)
        self.kernels[0].all_files = [
            KernelImage(td / 'kernel.old'),
            build,
        ]
        self.kernels[1].all_files = [
            KernelImage(td / 'kernel.new'),
            build,
        ]
        self.kernels[2].all_files = [
            build,
        ]
        self.kernels[3].all_files = [
            GenericFile(td / 'config-stray', KernelFileType.CONFIG),
            GenericFile(td / 'initrd-stray.img',
                        KernelFileType.INITRAMFS),
        ]

    def tearDown(self) -> None:
        self.td.cleanup()

    def test_remove_stray(self) -> None:
        self.assertEqual(
            list(remove_stray(self.kernels)),
            self.kernels[2:])

    def test_get_removable_files(self) -> None:
        td = Path(self.td.name)
        vmlinuz0 = td / 'kernel.old'
        config3 = td / 'config-stray'
        initrd3 = td / 'initrd-stray.img'
        self.assertEqual(
            list(get_removable_files({self.kernels[0]: ['old'],
                                      self.kernels[2]: ['no vmlinuz'],
                                      self.kernels[3]: ['no vmlinuz'],
                                      }, self.kernels)),
            [RemovableKernelFiles(self.kernels[0],
                                  ['old'],
                                  [vmlinuz0]),
             RemovableKernelFiles(self.kernels[2],
                                  ['no vmlinuz'],
                                  []),
             RemovableKernelFiles(self.kernels[3],
                                  ['no vmlinuz'],
                                  [config3, initrd3]),
             ])

    def test_removal_no_limit(self) -> None:
        self.assertEqual(
            get_removal_list(self.kernels,
                             limit=0),
            {self.kernels[2]: ['vmlinuz does not exist'],
             self.kernels[3]: ['vmlinuz does not exist'],
             })

    def test_removal_destructive(self) -> None:
        self.assertEqual(
            get_removal_list(self.kernels,
                             limit=1,
                             destructive=True),
            {self.kernels[2]: ['vmlinuz does not exist', 'unwanted'],
             self.kernels[3]: ['vmlinuz does not exist', 'unwanted'],
             self.kernels[0]: ['unwanted'],
             })

    def test_removal_no_bootloader(self) -> None:
        with self.assertRaises(SystemError):
            get_removal_list(self.kernels,
                             limit=1,
                             destructive=False)

    @unittest.expectedFailure
    def test_removal_bootloader(self) -> None:
        td = Path(self.td.name)

        class MockBootloader(object):
            name = 'mock'

            def __call__(self):
                yield str(td / 'does-not-exist')
                yield str(td / 'kernel.old')

        self.assertEqual(
            get_removal_list(self.kernels,
                             limit=1,
                             destructive=False,
                             bootloader=MockBootloader()),
            {self.kernels[2]: ['vmlinuz does not exist',
                               'not referenced by bootloader (mock)'],
             self.kernels[3]: ['vmlinuz does not exist',
                               'not referenced by bootloader (mock)'],
             })

    @patch('ecleankernel.process.os.uname')
    def test_removal_current(self,
                             uname: MagicMock
                             ) -> None:
        uname.return_value = (
            'Linux', 'localhost', 'old', '', 'x86_64')
        self.assertEqual(
            get_removal_list(self.kernels,
                             limit=1,
                             destructive=True),
            {self.kernels[2]: ['vmlinuz does not exist', 'unwanted'],
             self.kernels[3]: ['vmlinuz does not exist', 'unwanted'],
             })

    @patch('ecleankernel.process.os.uname')
    def test_removal_current_stray(self,
                                   uname: MagicMock
                                   ) -> None:
        uname.return_value = (
            'Linux', 'localhost', 'stray', '', 'x86_64')
        self.assertEqual(
            get_removal_list(self.kernels,
                             limit=1,
                             destructive=True),
            {self.kernels[3]: ['vmlinuz does not exist', 'unwanted'],
             self.kernels[0]: ['unwanted'],
             })
