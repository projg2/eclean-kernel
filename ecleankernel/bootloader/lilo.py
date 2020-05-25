# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import logging
import re
import typing

from ecleankernel.bootloader import Bootloader, BootloaderNotFound


class LILO(Bootloader):
    name = 'lilo'
    kernel_re = r'^\s*image\s*=\s*(?P<path>.+)\s*$'
    def_path: typing.Tuple[str, ...] = ('/etc/lilo.conf',)

    def __init__(self,
                 path: typing.Optional[str] = None
                 ) -> None:
        self._kernel_re = re.compile(self.kernel_re,
                                     re.MULTILINE | re.IGNORECASE)
        paths = path or self.def_path
        if not isinstance(paths, tuple):
            paths = (paths,)

        for p in paths:
            try:
                with open(p) as f:
                    logging.debug(f'{p} found')
                    self.path = p
                    self._content = f.read()
                    break
            except FileNotFoundError:
                pass
        else:
            raise BootloaderNotFound()

    def _get_kernels(self,
                     content: str
                     ) -> typing.Iterable[str]:
        logging.debug('matching...')
        for m in self._kernel_re.finditer(content):
            path = m.group('path')
            logging.debug(f'  regexp matched path {path}')
            logging.debug(f'    from line: {m.group(0)}')
            yield path

    def __call__(self) -> typing.Iterable[str]:
        return self._get_kernels(self._content)
