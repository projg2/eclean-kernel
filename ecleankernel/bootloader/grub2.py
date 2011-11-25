#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .grub import GRUB

class GRUB2(GRUB):
	name = 'grub2'
	kernel_re = r'^\s*linux\s*(\([^)]+\))?(?P<path>\S+)'
	def_path = '/boot/grub/grub.cfg'
