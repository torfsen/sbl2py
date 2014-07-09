#!/usr/bin/env python

"""
Various utilities.
"""


def remove_empty_lines(s):
	"""
	Remove empty lines from a string.
	"""
	return '\n'.join(line for line in s.split('\n') if line)


def prefix_lines(s, p):
	"""
	Prefix each line of ``s`` by ``p``.
	"""
	return p + ('\n' + p).join(s.split('\n'))


def extract(seq, f):
	"""
	Extract items from a possibly nested sequence.

	All items of the possibly nested sequence ``seq`` for which the callback
	``f`` returns ``True`` are returned in a list.
	"""
	try:
		it = iter(seq)
	except TypeError:
		return []
	items = []
	for item in it:
		if f(item):
			items.append(item)
		else:
			items.extend(extract(item, f))
	return items
