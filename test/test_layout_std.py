# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import tempfile
import typing
import unittest

from pathlib import Path

from ecleankernel.file import KernelFileType as KFT
from ecleankernel.file import GenericFile
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

    def test_find_modules(self) -> None:
        test_spec = [
            'boot/vmlinuz-1.2.3',
            'boot/System.map-1.2.3',
            'boot/config-1.2.3',
            'boot/initrd-1.2.3.img',
        ]
        test_spec += [f'{x}.old' for x in test_spec]
        test_spec += [
            'lib/modules/1.2.3/test.ko',
            'lib/modules/1.2.3/build/Makefile',
        ]
        with make_test_files(test_spec) as td_inst:
            td = Path(td_inst)
            boot = td / 'boot'
            modules = td / 'lib/modules'

            write_bzImage(boot / 'vmlinuz-1.2.3', b'1.2.3 test')
            write_bzImage(boot / 'vmlinuz-1.2.3.old', b'1.2.3 test')

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout().find_kernels(
                        boot_directory=boot,
                        module_directory=modules))),
                [('1.2.3',
                  [GenericFile(boot / 'System.map-1.2.3', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img', KFT.INITRAMFS),
                   GenericFile(boot / 'vmlinuz-1.2.3', KFT.KERNEL),
                   GenericFile(modules / '1.2.3', KFT.MODULES),
                   GenericFile(modules / '1.2.3/build', KFT.BUILD),
                   ],
                  '1.2.3'),
                 ('1.2.3.old',
                  [GenericFile(boot / 'System.map-1.2.3.old', KFT.SYSTEM_MAP),
                   GenericFile(boot / 'config-1.2.3.old', KFT.CONFIG),
                   GenericFile(boot / 'initrd-1.2.3.img.old', KFT.INITRAMFS),
                   GenericFile(boot / 'vmlinuz-1.2.3.old', KFT.KERNEL),
                   GenericFile(modules / '1.2.3', KFT.MODULES),
                   GenericFile(modules / '1.2.3/build', KFT.BUILD),
                   ],
                  '1.2.3')])

    def test_modules_only(self) -> None:
        test_spec = [
            'lib/modules/1.2.3/test.ko',
            'lib/modules/1.2.4/test.ko',
            'lib/modules/1.2.4/build/Makefile',
        ]
        with make_test_files(test_spec) as td_inst:
            td = Path(td_inst)
            boot = td / 'boot'
            modules = td / 'lib/modules'

            self.assertEqual(
                sorted(kernel_paths(
                    StdLayout().find_kernels(
                        boot_directory=boot,
                        module_directory=modules))),
                [('1.2.3',
                  [GenericFile(modules / '1.2.3', KFT.MODULES)
                   ],
                  None),
                 ('1.2.4',
                  [GenericFile(modules / '1.2.4', KFT.MODULES),
                   GenericFile(modules / '1.2.4/build', KFT.BUILD)
                   ],
                  None)])
