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
	try:
		return p + ('\n' + p).join(s.split('\n'))
	except Exception as e:
		import traceback
		traceback.print_exc()
		import pdb; pdb.set_trace()
		raise


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


def extract_strings(seq):
	"""
	Extract all strings from a possibly nested sequence.
	"""
	return extract(seq, lambda x: isinstance(x, basestring))


def annotate(text, caption, prefix='', single='> ', first='\\ ', middle=' | ', last='/ '):
	"""
	Annotate a block of text with a caption.

	``text`` is the text to be annotated. ``caption`` must be a single-line
	string.

	``prefix`` is a string that is prefixed before each added string. ``single``,
	``first``, ``middle`` and ``last`` are the prefixes for the caption bracket
	markers: ``single`` is used for texts that consist of a single line. For
	multi-line texts, the first line is marked with ``first``, the middle lines
	with ``middle`` and the last one with ``last``.
	"""
	lines = text.split('\n')
	lengths = [len(line) for line in lines]
	c = max(lengths)
	n = len(lines)
	for i in range(n):
		if n == 1:
			s = single
		elif i == 0:
			s = first
		elif i == n - 1:
			s = last
		else:
			s = middle
		lines[i] = lines[i] + ' ' * (c - lengths[i]) + prefix + s
	lines[n / 2] += caption
	return '\n'.join(lines)
