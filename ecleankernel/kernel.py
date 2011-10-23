#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from collections import defaultdict
from functools import partial
from glob import glob

def OnceProperty(f):
	def _get(propname, self):
		try:
			return getattr(self, propname)
		except AttributeError:
			return None

	def _set(propname, self, val):
		if hasattr(self, propname):
			raise KeyError('Value for %s already set' % propname)
		return setattr(self, propname, val)

	attrname = '_%s' % f.__name__
	return property(partial(_get, attrname), partial(_set, attrname))

class Kernel(object):
	""" An object representing a single kernel version. """

	def __init__(self, version):
		self._version = version

	@property
	def version(self):
		return self._version

	@OnceProperty
	def vmlinuz(self):
		pass

	@OnceProperty
	def systemmap(self):
		pass

	@OnceProperty
	def config(self):
		pass

	@OnceProperty
	def modules(self):
		pass

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
			if cat == 'modules' and '%s.old' % kv in kernels:
				kernels['%s.old' % kv].modules = m

	return kernels
