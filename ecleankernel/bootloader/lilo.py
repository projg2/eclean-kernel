# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .common import BootloaderNotFound

import errno
import re
import typing


class LILO(object):
    name = 'lilo'
    kernel_re = r'^\s*image\s*=\s*(?P<path>.+)\s*$'
    def_path: typing.Tuple[str, ...] = ('/etc/lilo.conf',)

    def __init__(self, debug=False, path=None):
        self._debug = debug
        self._kernel_re = re.compile(self.kernel_re,
                                     re.MULTILINE | re.IGNORECASE)
        paths = path or self.def_path
        if not isinstance(paths, tuple):
            paths = (paths,)

        for p in paths:
            try:
                with open(p) as f:
                    debug.print('%s found' % p)
                    self.path = p
                    self._content = f.read()
                    break
            except IOError as e:
                if e.errno != errno.ENOENT:
                    raise
        else:
            raise BootloaderNotFound()

    def _get_kernels(self, content):
        debug = self._debug

        debug.indent(heading='matching...')
        try:
            for m in self._kernel_re.finditer(content):
                path = m.group('path')
                debug.printf('regexp matched path %s', path)
                debug.indent()
                debug.printf('from line: %s', m.group(0))
                debug.outdent()
                yield path
        finally:
            debug.outdent()

    def __call__(self):
        return self._get_kernels(self._content)
