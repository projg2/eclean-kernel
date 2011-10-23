#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import re

def get_grub_kernels():
	kernel_re = re.compile(r'^\s*kernel\s*(\S+)',
			re.MULTILINE | re.IGNORECASE)

	f = open('/boot/grub/grub.conf')
	for m in kernel_re.finditer(f.read()):
		yield m.group(1)
	f.close()
