# vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path


class Symlinks(object):
    name = 'symlinks'

    def __init__(self, debug=False, path=None):
        self._debug = debug

    def __call__(self):
        for fn in ('vmlinuz', 'vmlinux', 'kernel', 'bzImage'):
            for suffix in ('', '.old'):
                f = '/boot/%s%s' % (fn, suffix)
                if os.path.exists(f):
                    yield f
