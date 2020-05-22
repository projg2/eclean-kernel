# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import tempfile
import typing
import unittest

from pathlib import Path

from ecleankernel.kernel import Kernel
from ecleankernel.layout.std import StdLayout


TEST_DATA_DIR = Path(__file__).parent / 'data'


def kernel_paths(kd: typing.List[Kernel]
                 ) -> typing.Iterable[typing.Tuple[
                      typing.Optional[str], ...]]:
    """Get iterable of tuples for matching a kernel dict"""
    for k in kd:
        yield (
            k.version,
            k.vmlinuz,
            k.systemmap,
            k.config,
            k.modules,
            k.build,
            k.initramfs,
            k.real_kv,
        )


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


class StdLayoutTests(unittest.TestCase):
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
                  str(boot / 'vmlinuz-1.2.3'),
                  str(boot / 'System.map-1.2.3'),
                  str(boot / 'config-1.2.3'),
                  str(modules / '1.2.3'),
                  str(modules / '1.2.3/build'),
                  str(boot / 'initrd-1.2.3.img'),
                  '1.2.3'),
                 ('1.2.3.old',
                  str(boot / 'vmlinuz-1.2.3.old'),
                  str(boot / 'System.map-1.2.3.old'),
                  str(boot / 'config-1.2.3.old'),
                  str(modules / '1.2.3'),
                  str(modules / '1.2.3/build'),
                  str(boot / 'initrd-1.2.3.img.old'),
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
                  None,
                  None,
                  None,
                  str(modules / '1.2.3'),
                  None,
                  None,
                  None),
                 ('1.2.4',
                  None,
                  None,
                  None,
                  str(modules / '1.2.4'),
                  str(modules / '1.2.4/build'),
                  None,
                  None)])
