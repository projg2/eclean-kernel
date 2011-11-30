#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .grub import GRUB
from .grub2 import GRUB2
from .lilo import LILO
from .yaboot import Yaboot
from .symlinks import Symlinks

import errno

bootloaders = (LILO, GRUB2, GRUB, Yaboot, Symlinks)

def get_bootloader(debug, requested = None):
	for bl in bootloaders:
		if requested in ('auto', bl.name):
			debug.printf('Trying bootloader %s', bl.name)
			debug.indent()
			try:
				return bl(debug = debug)
			except IOError as e:
				if e.errno != errno.ENOENT:
					raise
			finally:
				debug.outdent()
