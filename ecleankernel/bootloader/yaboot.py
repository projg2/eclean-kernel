# vim:fileencoding=utf-8
# (c) 2011-2020 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from ecleankernel.bootloader.lilo import LILO


class Yaboot(LILO):
    name = 'yaboot'
    def_path = ('/etc/yaboot.conf',)
