#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import os

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

def get_removal_list(kernels):
	""" Get a list of outdated kernels to remove. With explanations. """

	out = RemovedKernelDict()
	for k in remove_stray(kernels):
		out.add(k, 'vmlinuz does not exist')

	current = os.uname()[2]

	def not_current(kre):
		if kre[0].version == current:
			print('Preserving currently running kernel (%s)' % current)
			return False
		return True

	return filter(not_current, out)
