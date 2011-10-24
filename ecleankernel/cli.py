#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from optparse import OptionParser

from .kernel import find_kernels
from .process import get_removal_list

ecleankern_desc = '''
Remove old kernel versions, keeping either N newest kernels (with -n)
or only those which are referenced by a bootloader (with -a).
'''

def main(argv):
	parser = OptionParser(description = ecleankern_desc.strip())
	parser.add_option('-a', '--all',
			dest='all', action='store_true', default=False,
			help='Remove all kernels unless used by bootloader')
	parser.add_option('-b', '--bootloader',
			dest='bootloader', default='auto',
			help='Bootloader used (auto, grub, lilo, symlinks)')
	parser.add_option('-d', '--destructive',
			dest='destructive', action='store_true', default=False,
			help='Destructive mode: remove kernels even when referenced by bootloader')
	parser.add_option('-n', '--num',
			dest='num', type='int', default=0,
			help='Leave only newest NUM kernels (by mtime)')
	parser.add_option('-p', '--pretend',
			dest='pretend', action='store_true', default=False,
			help='Print the list of kernels to be removed and exit')
	(opts, args) = parser.parse_args(argv[1:])

	kernels = find_kernels()
	removals = get_removal_list(kernels,
			limit = None if opts.all else opts.num,
			bootloader = opts.bootloader,
			destructive = opts.destructive)

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
