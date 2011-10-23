#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from collections import defaultdict
from functools import partial
from glob import glob

class PathRef(str):
	def __init__(self, *args, **kwargs):
		self._refs = 0

	def ref(self):
		self._refs += 1

	def unref(self):
		self._refs -= 1
		if not self._refs:
			raise NotImplementedError('All refs gone, remove: %s' % self)

def OnceProperty(f):
	def _get(propname, self):
		try:
			return getattr(self, propname)
		except AttributeError:
			return None

	def _set(propname, self, val):
		if hasattr(self, propname):
			raise KeyError('Value for %s already set' % propname)
		val.ref()
		return setattr(self, propname, val)

	def _del(propname, self):
		if hasattr(self, propname):
			getattr(self, propname).unref()

	attrname = '_%s' % f.__name__
	funcs = [partial(x, attrname) for x in (_get, _set, _del)]
	return property(*funcs)

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

	def unrefall(self):
		del self.vmlinuz
		del self.systemmap
		del self.config
		del self.modules

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

	def __delitem__(self, kv):
		if kv not in self:
			raise KeyError(kv)
		self[kv].unrefall()
		defaultdict.__delitem__(self, kv)

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
			path = PathRef(m)
			setattr(kernels[kv], cat, path)
			if cat == 'modules' and '%s.old' % kv in kernels:
				kernels['%s.old' % kv].modules = path

	return kernels
