#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path, re

from .util import open_if_exists

def get_grub_kernels(debug = False):
	kernel_re = re.compile(r'^\s*kernel\s*(\S+)',
			re.MULTILINE | re.IGNORECASE)

	f = open_if_exists('/boot/grub/grub.conf')
	if debug:
		print('*** grub.conf %sfound' % ('' if f else 'not '))
	if f:
		for m in kernel_re.finditer(f.read()):
			path = m.group(1)
			if debug:
				print('**** regexp matched path %s' % path)
				print('     from line: %s' % m.group(0))
			if os.path.relpath(path, '/boot').startswith('..'):
				path = os.path.join('/boot', path)
				print('***** appending /boot, path now: %s' % path)
			yield path
		f.close()
