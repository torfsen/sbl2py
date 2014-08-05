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

import sys
import argparse

from sbl2py import translate_file

def main():
    parser = argparse.ArgumentParser(description='Compile Snowball to Python')
    parser.add_argument('infile', help='Input file (default STDIN)', nargs='?',
            type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('outfile', help='Output file (default STDOUT)', nargs='?',
            type=argparse.FileType('w'), default=sys.stdout)
    parser.add_argument('-d', '--debug', help='Generate code for easier debugging',
            action="store_true")
    args = parser.parse_args()
    args.outfile.write(translate_file(args.infile, debug=args.debug) + "\n")

if __name__ == '__main__':
    main()
