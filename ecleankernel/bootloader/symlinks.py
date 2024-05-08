# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

import os.path
import typing

from ecleankernel.bootloader import Bootloader


class Symlinks(Bootloader):
    name = 'symlinks'

    def __call__(self) -> typing.Iterable[str]:
        for fn in ('vmlinuz', 'vmlinux', 'kernel', 'bzImage'):
            for suffix in ('', '.old'):
                f = f'/boot/{fn}{suffix}'
                if os.path.exists(f):
                    yield f
