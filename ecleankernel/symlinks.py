#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path

def get_vmlinuz_symlinks():
	for p in ('/boot/vmlinuz', '/boot/vmlinuz.old'):
		yield os.path.realpath(p)
