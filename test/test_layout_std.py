# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import io
import os
import tempfile
import typing
import unittest

from pathlib import Path
from unittest.mock import patch

from ecleankernel.__main__ import main
from ecleankernel.file import KernelFileType as KFT
from ecleankernel.file import GenericFile, KernelImage, ModuleDirectory
from ecleankernel.kernel import Kernel
from ecleankernel.layout.std import StdLayout

from test.test_file import write_bzImage


TEST_DATA_DIR = Path(__file__).parent / 'data'


def kernel_paths(kd: typing.List[Kernel]
                 ) -> typing.Iterable[typing.Tuple[
                      str,
                      typing.List[GenericFile],
                      typing.Optional[str]]]:
    """Get iterable of tuples describing kernels"""
    for k in kd:
        yield (k.version,
               sorted(k.all_files, key=lambda f: f.path),
               k.real_kv)


def make_test_files(spec: typing.Iterable[str]
                    ) -> tempfile.TemporaryDirectory:
    """Create empty test files for paths in `spec`"""
    tempdir = tempfile.TemporaryDirectory()
    path = Path(tempdir.name)
    for fn in spec:
        fnpath = path / fn
        os.makedirs(fnpath.parent, exist_ok=True)
        with open(fnpath, 'w'):
            pass
    return tempdir


class StdLayoutTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        # prevent system configs from interfering
        os.environ['XDG_CONFIG_DIRS'] = '/dev/null'
        os.environ['XDG_CONFIG_HOME'] = '/dev/null'

    def create_layout(self) -> tempfile.TemporaryDirectory:
        """Create the typical layout"""
        test_spec = [
            'boot/vmlinuz-1.2.3',
            'boot/System.map-1.2.3',
            'boot/config-1.2.3',
            'boot/initrd-1.2.3.img',
        ]
        test_spec += [f'{x}.old' for x in test_spec]
        test_spec += [
            'boot/config-1.2.4',
            'boot/vmlinuz-1.2.2',
            'boot/vmlinuz-1.2.2.sig',
            'boot/System.map-1.2.2',
            'lib/modules/1.2.2/test.ko',
            'lib/modules/1.2.3/test.ko',
            'lib/modules/1.2.4/test.ko',
            'usr/src/linux/Makefile',
            # stray files
            'boot/System.map',
            'boot/config-',
        ]

        td = make_test_files(test_spec)
        path = Path(td.name)
        boot = path / 'boot'
        modules = path / 'lib/modules'

        write_bzImage(boot / 'vmlinuz-1.2.2', b'1.2.2 test')
        write_bzImage(boot / 'vmlinuz-1.2.3', b'1.2.3 test')
        write_bzImage(boot / 'vmlinuz-1.2.3.old', b'1.2.3 test')
        os.symlink('../../../usr/src/linux', modules / '1.2.2/build')
        os.symlink('../../../usr/src/linux', modules / '1.2.3/build')

        return td

    def assert_kernels(self,
                       root: Path,
                       k124: bool = True,
                       k123: bool = True,
                       k123old: bool = True,
                       k122: bool = True,
                       stray: bool = True
                       ) -> None:
        """Assert whether specified kernels were removed or kept"""
        files = {
            'boot/vmlinuz-1.2.3': k123,
            'boot/System.map-1.2.3': k123,
            'boot/config-1.2.3': k123,
            'boot/initrd-1.2.3.img': k123,
            'boot/vmlinuz-1.2.3.old': k123old,
            'boot/System.map-1.2.3.old': k123old,
            'boot/config-1.2.3.old': k123old,
            'boot/initrd-1.2.3.img.old': k123old,
            'boot/vmlinuz-1.2.2': k122,
            'boot/System.map-1.2.2': k122,
            'boot/config-1.2.4': k124,
            'lib/modules/1.2.2/test.ko': k122,
            'lib/modules/1.2.2': k122,
            'lib/modules/1.2.3/test.ko': k123 or k123old,
            'lib/modules/1.2.3': k123 or k123old,
            'lib/modules/1.2.4/test.ko': k124,
            'lib/modules/1.2.4': k124,
            'lib/modules': True,
            'usr/src/linux/Makefile': k122 or k123 or k123old,
            'usr/src/linux': k122 or k123 or k123old,
            'usr/src': True,
            'boot/System.map': stray,
            'boot/config-': stray,
            'boot': True,
        }
        expected_files = [f for f, exp in files.items() if exp]
        found_files = [f for f in files if (root / f).exists()]
        self.assertEqual(found_files, expected_files)

    def test_find_modules(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / 'boot'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout(root=path).find_kernels())),
                [('1.2.2',
                  [GenericFile(boot / 'System.map-1.2.2', KFT.SYSTEM_MAP),
                   KernelImage(boot / 'vmlinuz-1.2.2'),
                   ModuleDirectory(modules / '1.2.2'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [GenericFile(boot / 'System.map-1.2.3', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3'),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.3.old',
                  [GenericFile(boot / 'System.map-1.2.3.old', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3.old', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img.old', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3.old'),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [GenericFile(boot / 'config-1.2.4', KFT.CONFIG),
                   ModuleDirectory(modules / '1.2.4'),
                   ],
                  None)])

    def test_exclude_config(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / 'boot'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout(root=path).find_kernels(
                        exclusions=[KFT.CONFIG]))),
                [('1.2.2',
                  [GenericFile(boot / 'System.map-1.2.2', KFT.SYSTEM_MAP),
                   KernelImage(boot / 'vmlinuz-1.2.2'),
                   ModuleDirectory(modules / '1.2.2'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [GenericFile(boot / 'System.map-1.2.3', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'initrd-1.2.3.img', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3'),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.3.old',
                  [GenericFile(boot / 'System.map-1.2.3.old', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'initrd-1.2.3.img.old', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3.old'),
                   ModuleDirectory(modules / '1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [ModuleDirectory(modules / '1.2.4'),
                   ],
                  None)])

    def test_exclude_modules(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / 'boot'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout(root=path).find_kernels(
                        exclusions=[KFT.MODULES]))),
                [('1.2.2',
                  [GenericFile(boot / 'System.map-1.2.2', KFT.SYSTEM_MAP),
                   KernelImage(boot / 'vmlinuz-1.2.2'),
                   GenericFile(modules / '1.2.2/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [GenericFile(boot / 'System.map-1.2.3', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.3.old',
                  [GenericFile(boot / 'System.map-1.2.3.old', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3.old', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img.old', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3.old'),
                   GenericFile(modules / '1.2.3/../../../usr/src/linux',
                               KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [GenericFile(boot / 'config-1.2.4', KFT.CONFIG),
                   ],
                  None)])

    def test_exclude_build(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            boot = path / 'boot'
            modules = path / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout(root=path).find_kernels(
                        exclusions=[KFT.BUILD]))),
                [('1.2.2',
                  [GenericFile(boot / 'System.map-1.2.2', KFT.SYSTEM_MAP),
                   KernelImage(boot / 'vmlinuz-1.2.2'),
                   ModuleDirectory(modules / '1.2.2'),
                   ],
                  '1.2.2'),
                 ('1.2.3',
                  [GenericFile(boot / 'System.map-1.2.3', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3'),
                   ModuleDirectory(modules / '1.2.3'),
                   ],
                  '1.2.3'),
                 ('1.2.3.old',
                  [GenericFile(boot / 'System.map-1.2.3.old', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3.old', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img.old', KFT.INITRAMFS),
                   KernelImage(boot / 'vmlinuz-1.2.3.old'),
                   ModuleDirectory(modules / '1.2.3'),
                   ],
                  '1.2.3'),
                 ('1.2.4',
                  [GenericFile(boot / 'config-1.2.4', KFT.CONFIG),
                   ModuleDirectory(modules / '1.2.4'),
                   ],
                  None)])

    def test_modules_only(self) -> None:
        test_spec = [
            'lib/modules/1.2.3/test.ko',
            'lib/modules/1.2.4/test.ko',
            'usr/src/linux/Makefile',
        ]
        with make_test_files(test_spec) as td:
            path = Path(td)
            modules = path / 'lib/modules'

            os.symlink('../../../usr/src/linux', modules / '1.2.4/build')

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout(root=path).find_kernels())),
                [('1.2.3',
                  [ModuleDirectory(modules / '1.2.3')
                   ],
                  None),
                 ('1.2.4',
                  [ModuleDirectory(modules / '1.2.4'),
                   GenericFile(modules / '1.2.4/../../../usr/src/linux',
                               KFT.BUILD)
                   ],
                  None)])

    @patch('ecleankernel.__main__.sys.stdout', new_callable=io.StringIO)
    def test_main_list_kernels(self,
                               sout: io.StringIO
                               ) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--list-kernels', '--root', td, '--debug']),
                0)
            val = (x for x in sout.getvalue().splitlines()
                   if not x.startswith('- last modified:'))
            self.assertEqual('\n'.join(val), f'''
other 1.2.4 [None]
- config: {td}/boot/config-1.2.4
- modules: {td}/lib/modules/1.2.4
other 1.2.3 [1.2.3]
- systemmap: {td}/boot/System.map-1.2.3
- config: {td}/boot/config-1.2.3
- initramfs: {td}/boot/initrd-1.2.3.img
- vmlinuz: {td}/boot/vmlinuz-1.2.3
- modules: {td}/lib/modules/1.2.3
- build: {td}/lib/modules/1.2.3/../../../usr/src/linux
other 1.2.3.old [1.2.3]
- systemmap: {td}/boot/System.map-1.2.3.old
- config: {td}/boot/config-1.2.3.old
- initramfs: {td}/boot/initrd-1.2.3.img.old
- vmlinuz: {td}/boot/vmlinuz-1.2.3.old
- modules: {td}/lib/modules/1.2.3
- build: {td}/lib/modules/1.2.3/../../../usr/src/linux
other 1.2.2 [1.2.2]
- systemmap: {td}/boot/System.map-1.2.2
- vmlinuz: {td}/boot/vmlinuz-1.2.2
- modules: {td}/lib/modules/1.2.2
- build: {td}/lib/modules/1.2.2/../../../usr/src/linux'''.lstrip())
            self.assert_kernels(Path(td))

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
                                k122=False,
                                k123=False,
                                k123old=False,
                                k124=False)

    def test_main_remove_all_pretend(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--all', '--destructive', '--pretend',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td))

    def test_main_remove_n2(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--destructive', '-n', '2',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td),
                                k122=False,
                                k124=False)

    def test_main_remove_n2_pretend(self) -> None:
        with self.create_layout() as td:
            self.assertEqual(
                main(['--destructive', '-n', '2', '--pretend',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td))

    def test_wrong_layout_blspec(self) -> None:
        with self.create_layout() as td:
            with self.assertRaises(SystemExit) as e:
                main(['--destructive', '-n', '2', '--pretend',
                      '--layout', 'blspec',
                      '--root', td, '--debug', '--no-mount'])
            self.assertNotEqual(e.exception.code, 0)

    def test_config_file_system(self) -> None:
        with self.create_layout() as td:
            with open(Path(td) / 'eclean-kernel.rc', 'w') as f:
                f.write('-n "2"\n')
            os.environ['XDG_CONFIG_DIRS'] += f':{td}'

            self.assertEqual(
                main(['--destructive',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td),
                                k122=False,
                                k124=False)

    def test_config_file_user(self) -> None:
        with self.create_layout() as td:
            path = Path(td)
            os.mkdir(path / 'system')
            with open(path / 'system/eclean-kernel.rc', 'w') as f:
                f.write('-n 1\n')
            with open(path / 'eclean-kernel.rc', 'w') as f:
                f.write('-n "2"\n')
            os.environ['XDG_CONFIG_DIRS'] = str(path / 'system')
            os.environ['XDG_CONFIG_HOME'] = td

            self.assertEqual(
                main(['--destructive',
                      '--root', td, '--debug', '--no-mount']),
                0)
            self.assert_kernels(Path(td),
                                k122=False,
                                k124=False)
