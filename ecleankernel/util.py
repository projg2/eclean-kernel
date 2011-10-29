#	vim:fileencoding=utf-8
# (c) 2010 Michał Górny <mgorny@gentoo.org>
# Released under the terms of the 2-clause BSD license.

import errno

def open_if_exists(fn):
	"""
	Try opening the file for reading. If it doesn't exist, return None.
	Otherwise, return open file or re-raise the exception.
	"""
	try:
		return open(fn)
	except IOError as e:
		if e.errno == errno.ENOENT:
			return None
		raise
