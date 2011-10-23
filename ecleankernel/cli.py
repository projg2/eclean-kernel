#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .kernel import find_kernels
from .process import get_removal_list

def main(argv):
	k = find_kernels()
	removals = get_removal_list(k)

	if removals:
		print('These are the kernels which will be removed:')
	else:
		print('No outdated kernels found.')

	for k, reason in removals:
		print('- %s: %s' % (k.version, ', '.join(reason)))

	return 0
