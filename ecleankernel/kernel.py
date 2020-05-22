# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import os.path
import typing

from ecleankernel.file import GenericFile


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

    vmlinuz: typing.Optional[GenericFile] = None
    systemmap: typing.Optional[GenericFile] = None
    config: typing.Optional[GenericFile] = None
    modules: typing.Optional[GenericFile] = None
    build: typing.Optional[GenericFile] = None
    initramfs: typing.Optional[GenericFile] = None

    parts = ('vmlinuz', 'systemmap', 'config', 'initramfs',
             'modules', 'build')

    @property
    def all_files(self) -> typing.Iterator[GenericFile]:
        """Return a generator over all associated files (parts)"""
        for part in self.parts:
            f = getattr(self, part)
            if f is not None:
                yield f

    @property
    def real_kv(self):
        """Obtain the internal KV from kernel"""
        if self.vmlinuz is None:
            return None
        return self.vmlinuz.internal_version

    @property
    def mtime(self):
        # prefer vmlinuz, fallback to anything
        # XXX: or maybe max()? min()?
        for p in self.parts:
            f = getattr(self, p)
            if f is not None:
                return os.path.getmtime(f.path)

    def check_writable(self):
        for f in (self.vmlinuz, self.systemmap, self.config,
                  self.initramfs, self.modules, self.build):
            if f is not None and not os.access(f.path, os.W_OK):
                raise WriteAccessError(f.path)

    def __repr__(self):
        return "Kernel(%s, '%s%s%s%s%s%s')" % (repr(self.version),
                                               'V' if self.vmlinuz else ' ',
                                               'S' if self.systemmap else ' ',
                                               'C' if self.config else ' ',
                                               'I' if self.initramfs else ' ',
                                               'M' if self.modules else ' ',
                                               'B' if self.build else ' ')
