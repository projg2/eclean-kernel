# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import os.path
import struct
import typing


class WriteAccessError(Exception):
    def __init__(self, path):
        self._path = path
        Exception.__init__(
            self, '%s not writable, refusing to proceed.' % path)

    @property
    def friendly_desc(self):
        return '''The following file is not writable:
  %s

This usually indicates that you have insufficient permissions to run
eclean-kernel. The program needs to be able to remove all the files
associated with removed kernels. Lack of write access to some of them
will result in orphan files and therefore the program will refuse
to proceed.''' % self._path


class Kernel(object):
    """ An object representing a single kernel version. """

    def __init__(self, version):
        self._version = version

    @property
    def version(self):
        return self._version

    vmlinuz: typing.Optional[str] = None
    systemmap: typing.Optional[str] = None
    config: typing.Optional[str] = None
    modules: typing.Optional[str] = None
    build: typing.Optional[str] = None
    initramfs: typing.Optional[str] = None

    parts = ('vmlinuz', 'systemmap', 'config', 'initramfs',
             'modules', 'build')

    @property
    def all_files(self) -> typing.Iterator[str]:
        """Return a generator over all associated files (parts)"""
        for part in self.parts:
            path = getattr(self, part)
            if path is not None:
                yield path

    @property
    def real_kv(self):
        """ Obtain the KV from the kernel, as used by it. """
        vmlinuz = self.vmlinuz
        if vmlinuz is None:
            return None

        f = open(vmlinuz, 'rb')
        f.seek(0x200)
        buf = f.read(0x10)
        if buf[2:6] != b'HdrS':
            raise NotImplementedError('Invalid magic for kernel file'
                                      + ' %s (!= HdrS)' % vmlinuz)
        offset = struct.unpack_from('H', buf, 0x0e)[0]
        f.seek(offset - 0x10, 1)
        buf = f.read(0x100)  # XXX
        return buf.split(b' ', 1)[0].decode()

    @property
    def mtime(self):
        # prefer vmlinuz, fallback to anything
        # XXX: or maybe max()? min()?
        for p in self.parts:
            path = getattr(self, p)
            if path is not None:
                return os.path.getmtime(path)

    def check_writable(self):
        for path in (self.vmlinuz, self.systemmap, self.config,
                     self.initramfs, self.modules, self.build):
            if path and not os.access(path, os.W_OK):
                raise WriteAccessError(path)

    def __repr__(self):
        return "Kernel(%s, '%s%s%s%s%s%s')" % (repr(self.version),
                                               'V' if self.vmlinuz else ' ',
                                               'S' if self.systemmap else ' ',
                                               'C' if self.config else ' ',
                                               'I' if self.initramfs else ' ',
                                               'M' if self.modules else ' ',
                                               'B' if self.build else ' ')
