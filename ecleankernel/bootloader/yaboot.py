# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# SPDX-License-Identifier: GPL-2.0-or-later

from ecleankernel.bootloader.lilo import LILO


class Yaboot(LILO):
    name = 'yaboot'
    def_path = ('/etc/yaboot.conf',)
