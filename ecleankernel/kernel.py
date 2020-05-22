# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os
import os.path
import typing

from ecleankernel.file import GenericFile, KernelImage


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

    all_files: typing.List[GenericFile]
    version: str

    def __init__(self,
                 version: str
                 ) -> None:
        self.all_files = []
        self.version = version

    @property
    def real_kv(self) -> typing.Optional[str]:
        """Obtain the internal KV from kernel"""
        for f in self.all_files:
            if isinstance(f, KernelImage):
                return f.internal_version
        return None

    @property
    def mtime(self) -> float:
        """Get mtime for the oldest file in the set"""
        return min(os.path.getmtime(f.path) for f in self.all_files)

    def check_writable(self) -> None:
        """Check whether all files in the set are writable"""
        for f in self.all_files:
            if not os.access(f.path, os.W_OK):
                raise WriteAccessError(f.path)

    def __repr__(self):
        return f'Kernel({repr(self.version)})'
