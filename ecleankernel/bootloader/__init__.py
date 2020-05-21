# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from ecleankernel.bootloader.grub import GRUB
from ecleankernel.bootloader.grub2 import GRUB2
from ecleankernel.bootloader.lilo import LILO
from ecleankernel.bootloader.yaboot import Yaboot
from ecleankernel.bootloader.symlinks import Symlinks

from ecleankernel.bootloader.common import BootloaderNotFound

bootloaders = (LILO, GRUB2, GRUB, Yaboot, Symlinks)


def get_bootloader(debug, requested=None):
    for bl in bootloaders:
        if requested in ('auto', bl.name):
            debug.printf('Trying bootloader %s', bl.name)
            debug.indent()
            try:
                return bl(debug=debug)
            except BootloaderNotFound:
                pass
            finally:
                debug.outdent()
