#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os, os.path, shutil

from collections import defaultdict
from functools import partial
from glob import glob

class PathRef(str):
	def __init__(self, path):
		str.__init__(self, path)
		self._refs = 0

	def ref(self):
		self._refs += 1

	def unref(self):
		self._refs -= 1
		if not self._refs:
			print('- %s' % self)
			if os.path.isdir(self):
				shutil.rmtree(self)
			else:
				os.unlink(self)

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

	@OnceProperty
	def build(self):
		pass

	def unrefall(self):
		del self.vmlinuz
		del self.systemmap
		del self.config
		del self.modules
		del self.build

	def check_writable(self):
		for path in (self.vmlinuz, self.systemmap, self.config,
				self.modules, self.build):
			if path and not os.access(path, os.W_OK):
				raise OSError('%s not writable, refusing to proceed' % path)

	def __repr__(self):
		return "Kernel(%s, '%s%s%s%s%s')" % (repr(self.version),
				'V' if self.vmlinuz else ' ',
				'S' if self.systemmap else ' ',
				'C' if self.config else ' ',
				'M' if self.modules else ' ',
				'B' if self.build else ' ')

class PathDict(defaultdict):
	def __missing__(self, path):
		path = os.path.realpath(path)
		if path not in self:
			self[path] = PathRef(path)
		return self[path]

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

	def __iter__(self):
		return iter(self.values())

	def __repr__(self):
		return 'KernelDict(%s)' % ','.join(['\n\t%s' % repr(x) for x in self.values()])

def find_kernels():
	""" Find all files and directories related to installed kernels. """

	globs = (
		('vmlinuz', '/boot/vmlinuz-'),
		('vmlinuz', '/boot/vmlinux-'),
		('vmlinuz', '/boot/kernel-'),
		('vmlinuz', '/boot/bzImage-'),
		('systemmap', '/boot/System.map-'),
		('config', '/boot/config-'),
		('modules', '/lib/modules/')
	)

	# paths can repeat, so keep them sorted
	paths = PathDict()

	kernels = KernelDict()
	for cat, g in globs:
		for m in glob('%s*' % g):
			kv = m[len(g):]
			if kv.startswith('genkernel-'):
				try:
					kv = kv.split('-', 2)[2]
				except IndexError:
					pass

			path = paths[m]
			newk = kernels[kv]
			setattr(newk, cat, path)
			if cat == 'modules':
				builddir = paths[os.path.join(m, 'build')]
				if os.path.isdir(builddir):
					newk.build = builddir
				if '%s.old' % kv in kernels:
					# modules are not renamed to .old
					oldk = kernels['%s.old' % kv]
					oldk.modules = path
					if newk.build:
						oldk.build = newk.build
					# it seems that these are renamed .old sometimes
					if not oldk.systemmap and newk.systemmap:
						oldk.systemmap = newk.systemmap
					if not oldk.config and newk.config:
						oldk.config = newk.config

	return kernels
