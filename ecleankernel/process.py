#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os, os.path

from .lilo import get_lilo_kernels
from .symlinks import get_vmlinuz_symlinks

bootloaders = (
	('lilo', get_lilo_kernels),
	('symlinks', get_vmlinuz_symlinks),
)

class RemovedKernelDict(dict):
	def add(self, k, reason):
		if k not in self:
			self[k] = ()
		self[k] += (reason,)

	def __iter__(self):
		return iter(self.items())

def remove_stray(kernels):
	""" Remove files for non-existing kernels (without vmlinuz). """
	for k in kernels:
		if k.vmlinuz is None:
			yield k

def get_removal_list(kernels, limit = 0, bootloader = 'auto', destructive = False):
	""" Get a list of outdated kernels to remove. With explanations. """

	out = RemovedKernelDict()
	for k in remove_stray(kernels):
		out.add(k, 'vmlinuz does not exist')
	if len(out) == len(kernels):
		raise SystemError('No vmlinuz found. This seems ridiculous, aborting.')

	if limit is None or limit > 0:
		if not destructive:
			used = ()
			for bl, getfunc in bootloaders:
				if bootloader in ('auto', bl):
					try:
						used = getfunc()
					except Exception:
						pass
					else:
						lastbl = bl
						break

			realpaths = [os.path.realpath(x) for x in used]
			if not realpaths:
				raise SystemError('Unable to get kernels from bootloader config (%s)'
						% bootloader)

			prefix = '/boot/vmlinuz-'
			def unprefixify(filenames):
				for fn in filenames:
					if fn.startswith(prefix):
						yield fn[len(prefix):]
					else:
						print('Note: strangely named used kernel (%s)' % fn)

			used = frozenset(unprefixify(realpaths))

		if limit is not None:
			def getmtime(k):
				return os.path.getmtime(k.vmlinuz)

			ordered = sorted(kernels, key = getmtime, reverse = True)
			candidates = ordered[limit:]
		else:
			candidates = kernels

		for k in candidates:
			if destructive:
				out.add(k, 'unwanted')
			elif k.version not in used:
				out.add(k, 'not referenced by bootloader (%s)' % lastbl)

	current = os.uname()[2]

	def not_current(kre):
		if kre[0].version == current:
			print('Preserving currently running kernel (%s)' % current)
			return False
		return True

	return filter(not_current, out)
