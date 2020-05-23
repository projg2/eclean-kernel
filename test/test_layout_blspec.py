# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import tempfile
import unittest

from pathlib import Path

from ecleankernel.file import KernelFileType as KFT
from ecleankernel.file import GenericFile, KernelImage, ModuleDirectory
from ecleankernel.layout.blspec import BlSpecLayout

from test.test_file import write_bzImage
from test.test_layout_std import make_test_files, kernel_paths


class BlSpecLayoutTests(unittest.TestCase):
    maxDiff = None

    machine_id = '0123456789abcdef0123456789abcdef'

    def create_layout(self,
                      efi_subdir: bool = False
                      ) -> tempfile.TemporaryDirectory:
        subdir = 'EFI/' if efi_subdir else ''
        test_spec = [
            f'boot/{subdir}{self.machine_id}/1.2.3/initrd',
            f'boot/{subdir}{self.machine_id}/1.2.3/linux',
            f'boot/{subdir}{self.machine_id}/1.2.3/misc',
            'etc/machine-id',
            'lib/modules/1.2.3/test.ko',
            'usr/src/linux/Makefile',
            # stray files
            f'boot/{subdir}{self.machine_id}/1.2.2/initrd',
        ]

        td = make_test_files(test_spec)
        path = Path(td.name)
        bootsub = path / f'boot/{subdir}{self.machine_id}'
        modules = path / 'lib/modules'

        with open(path / 'etc/machine-id', 'w') as f:
            f.write(f'{self.machine_id}\n')
        write_bzImage(bootsub / '1.2.3/linux', b'1.2.3 test')
        os.symlink('../../../usr/src/linux', modules / '1.2.3/build')

        return td

    def test_accept_plain(self) -> None:
        with self.create_layout() as td:
            self.assertTrue(
                BlSpecLayout.is_acceptable(root=Path(td)))

    def test_accept_EFI(self) -> None:
        with self.create_layout(efi_subdir=True) as td:
            self.assertTrue(
                BlSpecLayout.is_acceptable(root=Path(td)))

    def test_accept_no_boot(self) -> None:
        test_spec = [
            'etc/machine-id',
        ]

        with make_test_files(test_spec) as td_inst:
            td = Path(td_inst)
            with open(td / 'etc/machine-id', 'w') as f:
                f.write(f'{self.machine_id}\n')

            self.assertFalse(
                BlSpecLayout.is_acceptable(root=td))

    def test_accept_no_machine_id(self) -> None:
        test_spec = [
            f'boot/EFI/{self.machine_id}/1.2.3/linux',
        ]

        with make_test_files(test_spec) as td_inst:
            td = Path(td_inst)
            self.assertFalse(
                BlSpecLayout.is_acceptable(root=td))

    def test_find_modules(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / f'boot/{self.machine_id}'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout().find_kernels(
                        root=path))),
                [('1.2.2',
                  [GenericFile(boot / '1.2.2/initrd', KFT.INITRAMFS),
                   ],
                  None),
                 ('1.2.3',
                  [GenericFile(boot / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(boot / '1.2.3/linux'),
                   GenericFile(boot / '1.2.3/misc', KFT.MISC),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ])

    def test_exclude_misc(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / f'boot/{self.machine_id}'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout().find_kernels(
                        exclusions=[KFT.MISC],
                        root=path))),
                [('1.2.2',
                  [GenericFile(boot / '1.2.2/initrd', KFT.INITRAMFS),
                   ],
                  None),
                 ('1.2.3',
                  [GenericFile(boot / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(boot / '1.2.3/linux'),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ])

    def test_exclude_modules(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / f'boot/{self.machine_id}'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout().find_kernels(
                        exclusions=[KFT.MODULES],
                        root=path))),
                [('1.2.2',
                  [GenericFile(boot / '1.2.2/initrd', KFT.INITRAMFS),
                   ],
                  None),
                 ('1.2.3',
                  [GenericFile(boot / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(boot / '1.2.3/linux'),
                   GenericFile(boot / '1.2.3/misc', KFT.MISC),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ])

    def test_exclude_build(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / f'boot/{self.machine_id}'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout().find_kernels(
                        exclusions=[KFT.BUILD],
                        root=path))),
                [('1.2.2',
                  [GenericFile(boot / '1.2.2/initrd', KFT.INITRAMFS),
                   ],
                  None),
                 ('1.2.3',
                  [GenericFile(boot / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(boot / '1.2.3/linux'),
                   GenericFile(boot / '1.2.3/misc', KFT.MISC),
                   ModuleDirectory(modules / '1.2.3'),
                   ],
                  '1.2.3'),
                 ])

    def test_find_modules_EFI(self) -> None:
        with self.create_layout(efi_subdir=True) as td:
            path = Path(td)
            boot = path / f'boot/EFI/{self.machine_id}'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout().find_kernels(
                        root=path))),
                [('1.2.2',
                  [GenericFile(boot / '1.2.2/initrd', KFT.INITRAMFS),
                   ],
                  None),
                 ('1.2.3',
                  [GenericFile(boot / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(boot / '1.2.3/linux'),
                   GenericFile(boot / '1.2.3/misc', KFT.MISC),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ])
