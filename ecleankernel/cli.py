#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from __future__ import print_function

from optparse import OptionParser

from .kernel import find_kernels
from .process import get_removal_list

ecleankern_desc = '''
Remove old kernel versions, keeping either N newest kernels (with -n)
or only those which are referenced by a bootloader (with -a).
'''

class NullDebugger(object):
	def __init__(self):
		self._indent = 1

	def print(self, msg):
		pass

	def printf(self, fstr, *args):
		self.print(fstr % args)

	def indent(self, n = 1, heading = None):
		if heading is not None:
			self.print(heading)
		self._indent += n

	def outdent(self, n = 1):
		self._indent -= n

class ConsoleDebugger(NullDebugger):
	def print(self, msg):
		ind = '*' * self._indent
		print('%s %s' % (ind, msg))

def main(argv):
	parser = OptionParser(description = ecleankern_desc.strip())
	parser.add_option('-a', '--all',
			dest='all', action='store_true', default=False,
			help='Remove all kernels unless used by bootloader')
	parser.add_option('-A', '--ask',
			dest='ask', action='store_true', default=False,
			help='Ask before removing each kernel')
	parser.add_option('-b', '--bootloader',
			dest='bootloader', default='auto',
			help='Bootloader used (auto, grub, lilo, symlinks)')
	parser.add_option('-d', '--destructive',
			dest='destructive', action='store_true', default=False,
			help='Destructive mode: remove kernels even when referenced by bootloader')
	parser.add_option('-D', '--debug',
			dest='debug', action='store_true', default=False,
			help='Enable debugging output')
	parser.add_option('-n', '--num',
			dest='num', type='int', default=0,
			help='Leave only newest NUM kernels (by mtime)')
	parser.add_option('-p', '--pretend',
			dest='pretend', action='store_true', default=False,
			help='Print the list of kernels to be removed and exit')
	(opts, args) = parser.parse_args(argv[1:])

	debug = ConsoleDebugger() if opts.debug else NullDebugger()

	kernels = find_kernels()
	removals = get_removal_list(kernels,
			limit = None if opts.all else opts.num,
			bootloader = opts.bootloader,
			destructive = opts.destructive,
			debug = debug)

	if not removals:
		print('No outdated kernels found.')
	elif opts.pretend:
		print('These are the kernels which would be removed:')

		for k, reason in removals:
			print('- %s: %s' % (k.version, ', '.join(reason)))
	else:
		for k, reason in removals:
			k.check_writable()

		for k, reason in removals:
			remove = True
			while opts.ask:
				ans = raw_input('Remove %s (%s)? [Yes/No]'
						% (k.version, ', '.join(reason))).lower()
				if 'yes'.startswith(ans):
					break
				elif 'no'.startswith(ans):
					remove = False
					break
				else:
					print('Invalid answer (%s).' % ans)

			if remove:
				print('* Removing kernel %s (%s)' % (k.version, ', '.join(reason)))
				del kernels[k.version]

	return 0
