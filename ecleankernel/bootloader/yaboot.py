#	vim:fileencoding=utf-8
# (c) 2011 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .lilo import LILO

class Yaboot(LILO):
	name = 'yaboot'
	def_path = '/etc/yaboot.conf'
