# vim:fileencoding=utf-8
# (c) 2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import tempfile
import time
import unittest

from pathlib import Path

from ecleankernel.file import GenericFile, KernelFileType
from ecleankernel.kernel import Kernel
from ecleankernel.sort import VersionSort, MTimeSort


class SortTests(unittest.TestCase):
    def test_version(self) -> None:
        vs = VersionSort()
        self.assertEqual(
            sorted([Kernel('4.14.0'),
                    Kernel('5.7.0-foo-rc3'),
                    Kernel('5.7.0-rc3'),
                    Kernel('5.7.0'),
                    Kernel('5.4.0'),
                    Kernel('5.6.10'),
                    Kernel('5.6-frobnicate'),
                    Kernel('5.6.0-frobnicate'),
                    Kernel('5.6.10-frobnicate'),
                    Kernel('4.7.11'),
                    Kernel('5.6.0'),
                    Kernel('5.6.10-rt-rt5'),
                    ], key=vs.key),
            [Kernel('4.7.11'),
             Kernel('4.14.0'),
             Kernel('5.4.0'),
             Kernel('5.6-frobnicate'),
             Kernel('5.6.0'),
             Kernel('5.6.0-frobnicate'),
             Kernel('5.6.10'),
             Kernel('5.6.10-frobnicate'),
             Kernel('5.6.10-rt-rt5'),
             Kernel('5.7.0-rc3'),
             Kernel('5.7.0'),
             Kernel('5.7.0-foo-rc3'),
             ])

    def test_mtime(self) -> None:
        ms = MTimeSort()
        with tempfile.TemporaryDirectory() as td_name:
            td = Path(td_name)

            ts = time.time()
            with open(td / 'f1', 'w') as f:
                os.utime(f.fileno(), (ts, ts))
            with open(td / 'f2', 'w') as f:
                os.utime(f.fileno(), (ts, ts-1))
            with open(td / 'f3', 'w') as f:
                os.utime(f.fileno(), (ts, ts-2))

            k1 = Kernel('1')
            k1.all_files = [GenericFile(td / 'f1', KernelFileType.MISC)]
            k2 = Kernel('2')
            k2.all_files = [GenericFile(td / 'f2', KernelFileType.MISC)]
            k3 = Kernel('3')
            k3.all_files = [GenericFile(td / 'f3', KernelFileType.MISC)]

            self.assertEqual(
                sorted([k1, k2, k3], key=ms.key),
                [k3, k2, k1])
