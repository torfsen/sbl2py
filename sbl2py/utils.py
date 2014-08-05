#!/usr/bin/env python
# vim:fileencoding=utf8

# Copyright (c) 2014 Florian Brucker
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Various utilities.
"""

import imp
import itertools
import math
import re


def remove_empty_lines(s):
    """
    Remove empty lines from a string.
    """
    return '\n'.join(line for line in s.splitlines() if line)

def prefix_lines(s, p):
    """
    Prefix each line of ``s`` by ``p``.
    """
    try:
        return p + ('\n' + p).join(s.splitlines())
    except Exception as e:
        import traceback
        traceback.print_exc()
        import pdb; pdb.set_trace()
        raise

def extract(seq, f):
    """
    Extract items from a possibly nested sequence.

    All items of the possibly nested sequence ``seq`` for which the
    callback ``f`` returns ``True`` are returned in a list.
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

def annotate(text, caption, prefix='', single='> ', first='\\ ', middle=' | ',
             last='/ '):
    """
    Annotate a block of text with a caption.

    ``text`` is the text to be annotated. ``caption`` must be a
    single-line string.

    ``prefix`` is a string that is prefixed before each added string.
    ``single``, ``first``, ``middle`` and ``last`` are the prefixes for
    the caption bracket markers: ``single`` is used for texts that
    consist of a single line. For multi-line texts, the first line is
    marked with ``first``, the middle lines with ``middle`` and the
    last one with ``last``.
    """
    lines = text.splitlines()
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

def group(iterable, size):
    """
    Group an iterable into tuples.
    """
    it = iter(iterable)
    while True:
        sub_it = itertools.islice(it, size)
        yield tuple([sub_it.next()] + list(sub_it))

def add_line_numbers(text, margin="  "):
    """
    Add line numbers to a text.
    """
    lines = text.splitlines()
    num_digits = math.floor(math.log10(len(lines))) + 1
    format_str = '%%%dd%s%%s' % (num_digits, margin)
    nums = xrange(1, len(lines) + 1)
    return '\n'.join(format_str % (n, line) for (n, line) in zip(nums, lines))

def module_from_code(name, code):
    """
    Dynamically create Python module from code string.
    """
    if isinstance(code, unicode):
        # Remove encoding declaration if present
        lines = code.splitlines()
        for i in (0, 1):
            if re.search(r"coding[:=]\s*([-\w.]+)", lines[i]) is not None:
                lines[i] = ''
                break
        code = '\n'.join(lines)

    module = imp.new_module(name)
    exec code in module.__dict__
    return module
