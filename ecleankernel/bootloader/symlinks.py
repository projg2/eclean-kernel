#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os.path

def get_vmlinuz_symlinks(debug = False):
	for fn in ('vmlinuz', 'vmlinux', 'kernel', 'bzImage'):
		for suffix in ('', '.old'):
			f = '/boot/%s%s' % (fn, suffix)
			if os.path.exists(f):
				yield f
