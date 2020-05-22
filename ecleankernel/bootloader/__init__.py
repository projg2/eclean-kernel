# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import logging

from ecleankernel.bootloader.common import BootloaderNotFound
from ecleankernel.bootloader.grub import GRUB
from ecleankernel.bootloader.grub2 import GRUB2
from ecleankernel.bootloader.lilo import LILO
from ecleankernel.bootloader.yaboot import Yaboot
from ecleankernel.bootloader.symlinks import Symlinks

bootloaders = (LILO, GRUB2, GRUB, Yaboot, Symlinks)


def get_bootloader(requested=None):
    for bl in bootloaders:
        if requested in ('auto', bl.name):
            logging.debug(f'Trying bootloader {bl.name}')
            try:
                return bl()
            except BootloaderNotFound:
                pass
