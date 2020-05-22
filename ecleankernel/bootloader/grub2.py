# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import errno
import logging
import subprocess

from ecleankernel.bootloader.grub import GRUB

grub2_autogen_header = '''#
# DO NOT EDIT THIS FILE
#
# It is automatically generated by grub2-mkconfig'''


class GRUB2(GRUB):
    name = 'grub2'
    kernel_re = r'^\s*linux\s*(\([^)]+\))?(?P<path>\S+)'
    def_path = ('/boot/grub/grub.cfg', '/boot/grub2/grub.cfg')

    def _get_kernels(self, content):
        self._autogen = content.startswith(grub2_autogen_header)

        if self._autogen:
            logging.debug('Config is autogenerated, ignoring')
            self.postrm = self._postrm
            return ()
        return GRUB._get_kernels(self, content)

    def _postrm(self):
        if self._autogen:
            logging.debug('Calling grub2-mkconfig')
            try:
                subprocess.call(['grub-mkconfig', '-o', self.path])
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
            else:
                subprocess.call(['grub2-mkconfig', '-o', self.path])
