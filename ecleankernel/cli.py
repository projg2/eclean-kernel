#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .kernel import find_kernels

def main(argv):
	print find_kernels()

	return 0
