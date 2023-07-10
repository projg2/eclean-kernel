# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import tempfile
import unittest

from pathlib import Path

from ecleankernel.__main__ import main
from ecleankernel.file import KernelFileType as KFT
from ecleankernel.file import (
    GenericFile,
    KernelImage,
    ModuleDirectory,
    EmptyDirectory,
    )
from ecleankernel.layout import LayoutNotFound
from ecleankernel.layout.blspec import BlSpecLayout

from test.test_file import write_bzImage
from test.test_layout_std import make_test_files, kernel_paths


class BlSpecLayoutTests(unittest.TestCase):
    maxDiff = None

    machine_id = '0123456789abcdef0123456789abcdef'
    entry_token = "testsys"

    def setUp(self) -> None:
        # prevent system configs from interfering
        os.environ['XDG_CONFIG_DIRS'] = '/dev/null'
        os.environ['XDG_CONFIG_HOME'] = '/dev/null'

    def create_layout(self,
                      efi_subdir: bool = False,
                      entry_token: bool = False,
                      ) -> tempfile.TemporaryDirectory:
        subdir = 'EFI/' if efi_subdir else ''
        entry = self.entry_token if entry_token else self.machine_id
        test_spec = [
            f"boot/{subdir}/EFI/Linux/{entry}-1.2.6.efi",
            f"boot/{subdir}/EFI/Linux/{entry}-1.2.5.efi",
            f"boot/{subdir}/{entry}/1.2.5/initrd",
            f"boot/{subdir}/{entry}/1.2.5/linux",
            f"boot/{subdir}/{entry}/1.2.4/initrd",
            f"boot/{subdir}/{entry}/1.2.3/initrd",
            f"boot/{subdir}/{entry}/1.2.3/linux",
            f"boot/{subdir}/{entry}/1.2.3/misc",
            f"boot/{subdir}/{entry}/1.2.2/initrd",
            f"boot/{subdir}/{entry}/1.2.2/linux",
            f"boot/{subdir}/{entry}/1.2.2/.hidden-blocker",
            f"boot/{subdir}/{entry}/1.2.1/initrd",
            f"boot/{subdir}/{entry}/1.2.1/linux",
            f"boot/{subdir}/loader/entries",
            'etc/machine-id',
            'lib/modules/1.2.6/test.ko',
            'lib/modules/1.2.5/test.ko',
            'lib/modules/1.2.4/test.ko',
            'lib/modules/1.2.3/test.ko',
            'lib/modules/1.2.2/test.ko',
            'lib/modules/1.2.1/test.ko',
            'usr/src/linux/Makefile',
        ]

        if entry_token:
            test_spec.append("etc/kernel/entry-token")

        td = make_test_files(test_spec)
        path = Path(td.name)
        bootsub = path / f"boot/{subdir}"
        modules = path / 'lib/modules'

        with open(path / 'etc/machine-id', 'w') as f:
            f.write(f'{self.machine_id}\n')
        if entry_token:
            with open(path / "etc/kernel/entry-token", "w") as f:
                f.write(f"{self.entry_token}\n")
        write_bzImage(bootsub / f"EFI/Linux/{entry}-1.2.6.efi", b'1.2.6 test')
        write_bzImage(bootsub / f"EFI/Linux/{entry}-1.2.5.efi", b'1.2.5 test')
        write_bzImage(bootsub / f"{entry}/1.2.5/linux", b'1.2.5 test')
        write_bzImage(bootsub / f"{entry}/1.2.3/linux", b'1.2.3 test')
        write_bzImage(bootsub / f"{entry}/1.2.2/linux", b'1.2.2 test')
        write_bzImage(bootsub / f"{entry}/1.2.1/linux", b'1.2.1 test')
        os.symlink('../../../usr/src/linux', modules / '1.2.6/build')
        os.symlink('../../../usr/src/linux', modules / '1.2.5/build')
        os.symlink('../../../usr/src/linux', modules / '1.2.3/build')
        os.symlink('../../../usr/src/linux', modules / '1.2.2/build')

        return td

    def assert_kernels(self,
                       root: Path,
                       efi_subdir: bool = False,
                       k126: bool = True,
                       k125: bool = True,
                       k124: bool = True,
                       k123: bool = True,
                       k122: bool = True,
                       k121: bool = True
                       ) -> None:
        """Assert whether specified kernels were removed or kept"""
        subdir = 'EFI/' if efi_subdir else ''
        files = {
            f'boot/{subdir}/EFI/Linux/{self.machine_id}-1.2.6.efi': k126,
            f'boot/{subdir}/EFI/Linux/{self.machine_id}-1.2.5.efi': k125,
            f'boot/{subdir}{self.machine_id}/1.2.5/initrd': k125,
            f'boot/{subdir}{self.machine_id}/1.2.5/linux': k125,
            f'boot/{subdir}{self.machine_id}/1.2.5': k125,
            f'boot/{subdir}{self.machine_id}/1.2.4/initrd': k124,
            f'boot/{subdir}{self.machine_id}/1.2.4': k124,
            f'boot/{subdir}{self.machine_id}/1.2.3/initrd': k123,
            f'boot/{subdir}{self.machine_id}/1.2.3/linux': k123,
            f'boot/{subdir}{self.machine_id}/1.2.3/misc': k123,
            f'boot/{subdir}{self.machine_id}/1.2.3': k123,
            f'boot/{subdir}{self.machine_id}/1.2.2/initrd': k122,
            f'boot/{subdir}{self.machine_id}/1.2.2/linux': k122,
            f'boot/{subdir}{self.machine_id}/1.2.2/.hidden-blocker': True,
            f'boot/{subdir}{self.machine_id}/1.2.2': True,
            f'boot/{subdir}{self.machine_id}/1.2.1/initrd': k121,
            f'boot/{subdir}{self.machine_id}/1.2.1/linux': k121,
            f'boot/{subdir}{self.machine_id}/1.2.1': k121,
            f'boot/{subdir}{self.machine_id}': True,
            f"boot/{subdir}/loader/entries": True,
            'etc/machine-id': True,
            'lib/modules/1.2.6/test.ko': k126,
            'lib/modules/1.2.6': k126,
            'lib/modules/1.2.5/test.ko': k125,
            'lib/modules/1.2.5': k125,
            'lib/modules/1.2.4/test.ko': k124,
            'lib/modules/1.2.4': k124,
            'lib/modules/1.2.3/test.ko': k123,
            'lib/modules/1.2.3': k123,
            'lib/modules/1.2.2/test.ko': k122,
            'lib/modules/1.2.2': k122,
            'lib/modules/1.2.1/test.ko': k121,
            'lib/modules/1.2.1': k121,
            'lib/modules': True,
            'usr/src/linux/Makefile': k126 or k125 or k123 or k122,
            'usr/src/linux': k126 or k125 or k123 or k122,
            'usr/src': True,
        }
        expected_files = [f for f, exp in files.items() if exp]
        found_files = [f for f in files if (root / f).exists()]
        self.assertEqual(found_files, expected_files)

    def test_accept_plain(self) -> None:
        with self.create_layout() as td:
            BlSpecLayout(root=Path(td))

    def test_accept_EFI(self) -> None:
        with self.create_layout(efi_subdir=True) as td:
            BlSpecLayout(root=Path(td))

    def test_accept_entry_token(self) -> None:
        with self.create_layout(entry_token=True) as td:
            BlSpecLayout(root=Path(td))

    def test_accept_no_boot(self) -> None:
        test_spec = [
            'etc/machine-id',
        ]

        with make_test_files(test_spec) as td_inst:
            td = Path(td_inst)
            with open(td / 'etc/machine-id', 'w') as f:
                f.write(f'{self.machine_id}\n')

            with self.assertRaises(LayoutNotFound):
                BlSpecLayout(root=Path(td))

    def test_accept_no_machine_id(self) -> None:
        test_spec = [
            f'boot/EFI/{self.machine_id}/1.2.3/linux',
        ]

        with make_test_files(test_spec) as td_inst:
            td = Path(td_inst)
            with self.assertRaises(LayoutNotFound):
                BlSpecLayout(root=Path(td))

    def test_find_modules(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            blspath = path / f"boot/{self.machine_id}"
            ukipath = path / "boot/EFI/Linux"
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout(root=path).find_kernels()),
                    key=lambda ver: ver[0]),
                [('1.2.1',
                  [EmptyDirectory(blspath / '1.2.1'),
                   GenericFile(blspath / '1.2.1/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.1/linux'),
                   ModuleDirectory(modules / '1.2.1'),
                   ],
                  '1.2.1'),
                 ('1.2.2',
                  [EmptyDirectory(blspath / '1.2.2'),
                   GenericFile(blspath / '1.2.2/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.2/linux'),
                   ModuleDirectory(modules / '1.2.2'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [EmptyDirectory(blspath / '1.2.3'),
                   GenericFile(blspath / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.3/linux'),
                   GenericFile(blspath / '1.2.3/misc', KFT.MISC),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [EmptyDirectory(blspath / '1.2.4'),
                   GenericFile(blspath / '1.2.4/initrd', KFT.INITRAMFS),
                   ModuleDirectory(modules / '1.2.4'),
                   ],
                  None),
                 ('1.2.5',
                  [EmptyDirectory(blspath / '1.2.5'),
                   GenericFile(blspath / '1.2.5/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.5/linux'),
                   ModuleDirectory(modules / '1.2.5'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.5',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.5.efi"),
                   ModuleDirectory(modules / '1.2.5'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.6',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.6.efi"),
                   ModuleDirectory(modules / '1.2.6'),
                   GenericFile(modules / '1.2.6/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.6'),
                 ])

    def test_exclude_misc(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            blspath = path / f"boot/{self.machine_id}"
            ukipath = path / "boot/EFI/Linux"
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout(root=path).find_kernels(
                        exclusions=[KFT.MISC])),
                       key=lambda ver: ver[0]),
                [('1.2.1',
                  [EmptyDirectory(blspath / '1.2.1'),
                   GenericFile(blspath / '1.2.1/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.1/linux'),
                   ModuleDirectory(modules / '1.2.1'),
                   ],
                  '1.2.1'),
                 ('1.2.2',
                  [EmptyDirectory(blspath / '1.2.2'),
                   GenericFile(blspath / '1.2.2/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.2/linux'),
                   ModuleDirectory(modules / '1.2.2'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [EmptyDirectory(blspath / '1.2.3'),
                   GenericFile(blspath / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.3/linux'),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [EmptyDirectory(blspath / '1.2.4'),
                   GenericFile(blspath / '1.2.4/initrd', KFT.INITRAMFS),
                   ModuleDirectory(modules / '1.2.4'),
                   ],
                  None),
                 ('1.2.5',
                  [EmptyDirectory(blspath / '1.2.5'),
                   GenericFile(blspath / '1.2.5/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.5/linux'),
                   ModuleDirectory(modules / '1.2.5'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.5',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.5.efi"),
                   ModuleDirectory(modules / '1.2.5'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.6',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.6.efi"),
                   ModuleDirectory(modules / '1.2.6'),
                   GenericFile(modules / '1.2.6/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.6'),
                 ])

    def test_exclude_modules(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            blspath = path / f"boot/{self.machine_id}"
            ukipath = path / "boot/EFI/Linux"
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout(root=path).find_kernels(
                        exclusions=[KFT.MODULES])),
                       key=lambda ver: ver[0]),
                [('1.2.1',
                  [EmptyDirectory(blspath / '1.2.1'),
                   GenericFile(blspath / '1.2.1/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.1/linux'),
                   ],
                  '1.2.1'),
                 ('1.2.2',
                  [EmptyDirectory(blspath / '1.2.2'),
                   GenericFile(blspath / '1.2.2/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.2/linux'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [EmptyDirectory(blspath / '1.2.3'),
                   GenericFile(blspath / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.3/linux'),
                   GenericFile(blspath / '1.2.3/misc', KFT.MISC),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [EmptyDirectory(blspath / '1.2.4'),
                   GenericFile(blspath / '1.2.4/initrd', KFT.INITRAMFS),
                   ],
                  None),
                 ('1.2.5',
                  [EmptyDirectory(blspath / '1.2.5'),
                   GenericFile(blspath / '1.2.5/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.5/linux'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.5',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.5.efi"),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.6',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.6.efi"),
                   GenericFile(modules / '1.2.6/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.6'),
                 ])

    def test_exclude_build(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            blspath = path / f"boot/{self.machine_id}"
            ukipath = path / "boot/EFI/Linux"
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout(root=path).find_kernels(
                        exclusions=[KFT.BUILD])),
                       key=lambda ver: ver[0]),
                [('1.2.1',
                  [EmptyDirectory(blspath / '1.2.1'),
                   GenericFile(blspath / '1.2.1/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.1/linux'),
                   ModuleDirectory(modules / '1.2.1'),
                   ],
                  '1.2.1'),
                 ('1.2.2',
                  [EmptyDirectory(blspath / '1.2.2'),
                   GenericFile(blspath / '1.2.2/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.2/linux'),
                   ModuleDirectory(modules / '1.2.2'),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [EmptyDirectory(blspath / '1.2.3'),
                   GenericFile(blspath / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.3/linux'),
                   GenericFile(blspath / '1.2.3/misc', KFT.MISC),
                   ModuleDirectory(modules / '1.2.3'),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [EmptyDirectory(blspath / '1.2.4'),
                   GenericFile(blspath / '1.2.4/initrd', KFT.INITRAMFS),
                   ModuleDirectory(modules / '1.2.4'),
                   ],
                  None),
                 ('1.2.5',
                  [EmptyDirectory(blspath / '1.2.5'),
                   GenericFile(blspath / '1.2.5/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.5/linux'),
                   ModuleDirectory(modules / '1.2.5'),
                   ],
                  '1.2.5'),
                 ('1.2.5',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.5.efi"),
                   ModuleDirectory(modules / '1.2.5'),
                   ],
                  '1.2.5'),
                 ('1.2.6',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.6.efi"),
                   ModuleDirectory(modules / '1.2.6'),
                   ],
                  '1.2.6'),
                 ])

    def test_find_modules_EFI(self) -> None:
        with self.create_layout(efi_subdir=True) as td:
            path = Path(td)
            blspath = path / f"boot/EFI/{self.machine_id}"
            ukipath = path / "boot/EFI/EFI/Linux"
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    BlSpecLayout(root=path).find_kernels()),
                    key=lambda ver: ver[0]),
                [('1.2.1',
                  [EmptyDirectory(blspath / '1.2.1'),
                   GenericFile(blspath / '1.2.1/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.1/linux'),
                   ModuleDirectory(modules / '1.2.1'),
                   ],
                  '1.2.1'),
                 ('1.2.2',
                  [EmptyDirectory(blspath / '1.2.2'),
                   GenericFile(blspath / '1.2.2/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.2/linux'),
                   ModuleDirectory(modules / '1.2.2'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [EmptyDirectory(blspath / '1.2.3'),
                   GenericFile(blspath / '1.2.3/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.3/linux'),
                   GenericFile(blspath / '1.2.3/misc', KFT.MISC),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [EmptyDirectory(blspath / '1.2.4'),
                   GenericFile(blspath / '1.2.4/initrd', KFT.INITRAMFS),
                   ModuleDirectory(modules / '1.2.4'),
                   ],
                  None),
                 ('1.2.5',
                  [EmptyDirectory(blspath / '1.2.5'),
                   GenericFile(blspath / '1.2.5/initrd', KFT.INITRAMFS),
                   KernelImage(blspath / '1.2.5/linux'),
                   ModuleDirectory(modules / '1.2.5'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.5',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.5.efi"),
                   ModuleDirectory(modules / '1.2.5'),
                   GenericFile(modules / '1.2.5/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.5'),
                 ('1.2.6',
                  [KernelImage(ukipath / f"{self.machine_id}-1.2.6.efi"),
                   ModuleDirectory(modules / '1.2.6'),
                   GenericFile(modules / '1.2.6/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.6'),
                 ])

    def test_main_remove(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--destructive',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td),
                                k124=False)

    def test_main_remove_pretend(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--destructive', '--pretend',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td))

    def test_main_remove_all(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--all', '--destructive',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td),
                                k121=False,
                                k122=False,
                                k123=False,
                                k124=False,
                                k125=False,
                                k126=False)

    def test_main_remove_all_pretend(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--all', '--destructive', '--pretend',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td))

    def test_main_remove_n3(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--destructive', '-n', '3',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td),
                                k121=False,
                                k122=False,
                                k123=False,
                                k124=False)

    def test_main_remove_n3_pretend(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--destructive', '-n', '3', '--pretend',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td))

    def test_wrong_layout_std(self) -> None:
        with self.create_layout() as td:
            with self.assertRaises(SystemError):
                main(['--destructive', '-n', '3', '--pretend',
                      '--layout', 'std',
                      '--root', td, '--debug', '--no-mount'])
