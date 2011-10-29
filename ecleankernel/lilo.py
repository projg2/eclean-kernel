#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import re

from .util import open_if_exists

def get_lilo_kernels(debug = False):
	kernel_re = re.compile(r'^\s*image\s*=\s*(.+)\s*$',
			re.MULTILINE | re.IGNORECASE)

	f = open_if_exists('/etc/lilo.conf')
	if f:
		for m in kernel_re.finditer(f.read()):
			yield m.group(1)
		f.close()
