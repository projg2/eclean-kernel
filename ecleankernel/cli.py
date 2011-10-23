#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from optparse import OptionParser

from .kernel import find_kernels
from .process import get_removal_list

def main(argv):
	parser = OptionParser()
	parser.add_option('-p', '--pretend',
			dest='pretend', action='store_true', default=False,
			help='Print the list of kernels to be removed and exit')
	(opts, args) = parser.parse_args(argv[1:])

	kernels = find_kernels()
	removals = get_removal_list(kernels)

	if not removals:
		print('No outdated kernels found.')
	elif opts.pretend:
		print('These are the kernels which would be removed:')

		for k, reason in removals:
			print('- %s: %s' % (k.version, ', '.join(reason)))
	else:
		for k, reason in removals:
			print('* Removing kernel %s (%s)' % (k.version, ', '.join(reason)))
			del kernels[k.version]

	return 0
