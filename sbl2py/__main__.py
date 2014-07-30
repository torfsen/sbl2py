#!/usr/bin/env python

import sys
import argparse

from sbl2py import translate_file

parser = argparse.ArgumentParser(description='Compile Snowball to Python')
parser.add_argument('infile', help='Input file (default STDIN)', nargs='?',
		type=argparse.FileType('r'), default=sys.stdin)
parser.add_argument('outfile', help='Output file (default STDOUT)', nargs='?',
		type=argparse.FileType('w'), default=sys.stdout)
parser.add_argument('-d', '--debug', help='Generate code for easier debugging',
		action="store_true")
args = parser.parse_args()

args.outfile.write(translate_file(args.infile, debug=args.debug) + "\n")
