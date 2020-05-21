# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import typing
import unittest

from pathlib import Path

from ecleankernel.kernel import Kernel, KernelDict
from ecleankernel.layout.std import StdLayout


TEST_DATA_DIR = Path(__file__).parent / 'data'


def kernel_paths(kd: KernelDict
                 ) -> typing.List[typing.Tuple[str, ...]]:
    """Get iterable of tuples for matching a `KernelDict`"""
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


class StdLayoutTests(unittest.TestCase):
    def test_find_modules(self) -> None:
        boot = TEST_DATA_DIR / 'std' / 'boot'
        modules = TEST_DATA_DIR / 'std' / 'lib' / 'modules'
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
              None,
              str(boot / 'initrd-1.2.3.img'),
              '1.2.3'),
             ('1.2.3.old',
              str(boot / 'vmlinuz-1.2.3.old'),
              str(boot / 'System.map-1.2.3.old'),
              str(boot / 'config-1.2.3.old'),
              str(modules / '1.2.3'),
              None,
              str(boot / 'initrd-1.2.3.img.old'),
              '1.2.3')])
