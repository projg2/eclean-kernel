#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .lilo import LILO

import os.path

class GRUB(LILO):
	name = 'grub'
	kernel_re = r'^\s*(kernel|module)\s*(\([^)]+\))?(?P<path>\S+)'
	def_path = '/boot/grub/grub.conf'

	def _get_kernels(self, *args, **kwargs):
		debug = self._debug

		for path in LILO._get_kernels(self, *args, **kwargs):
			if os.path.relpath(path, '/boot').startswith('..'):
				path = os.path.join('/boot', os.path.relpath(path, '/'))
				debug.indent()
				debug.printf('appending /boot, path now: %s', path)
				debug.outdent()
			yield path
