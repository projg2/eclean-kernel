#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

from .kernel import find_kernels
from .process import get_removal_list

def main(argv):
	k = find_kernels()
	print get_removal_list(k)

	return 0
