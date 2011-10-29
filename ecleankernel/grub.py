#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import re

from .util import open_if_exists

def get_grub_kernels():
	kernel_re = re.compile(r'^\s*kernel\s*(\S+)',
			re.MULTILINE | re.IGNORECASE)

	f = open_if_exists('/boot/grub/grub.conf')
	if f:
		for m in kernel_re.finditer(f.read()):
			yield m.group(1)
		f.close()
