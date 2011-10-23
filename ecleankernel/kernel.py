#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from collections import defaultdict
from glob import glob

class Kernel(object):
	""" An object representing a single kernel version. """

	def __init__(self, version):
		self.version = version
		self.vmlinuz = None
		self.systemmap = None
		self.config = None
		self.modules = None

	def __repr__(self):
		return "Kernel(%s, '%s%s%s%s')" % (repr(self.version),
				'V' if self.vmlinuz else ' ',
				'S' if self.systemmap else ' ',
				'C' if self.config else ' ',
				'M' if self.modules else ' ')

class KernelDict(defaultdict):
	def __missing__(self, kv):
		k = Kernel(kv)
		self[kv] = k
		return k

	def __repr__(self):
		return 'KernelDict(%s)' % ','.join(['\n\t%s' % repr(x) for x in self.values()])

def find_kernels():
	""" Find all files and directories related to installed kernels. """

	globs = (
		('vmlinuz', '/boot/vmlinuz-'),
		('systemmap', '/boot/System.map-'),
		('config', '/boot/config-'),
		('modules', '/lib/modules/')
	)

	kernels = KernelDict()
	for cat, g in globs:
		for m in glob('%s*' % g):
			kv = m[len(g):]
			setattr(kernels[kv], cat, m)

	return kernels
