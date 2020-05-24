# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import logging
import os.path
import typing

from ecleankernel.bootloader.lilo import LILO


class GRUB(LILO):
    name = 'grub'
    kernel_re = r'^\s*(kernel|module)\s*(\([^)]+\))?(?P<path>\S+)'
    def_path = ('/boot/grub/menu.lst', '/boot/grub/grub.conf')

    def _get_kernels(self,
                     content: str
                     ) -> typing.Iterable[str]:
        for path in LILO._get_kernels(self, content):
            if os.path.relpath(path, '/boot').startswith('..'):
                path = os.path.join('/boot', os.path.relpath(path, '/'))
                logging.debug(f'appending /boot, path now: {path}')
            yield path
