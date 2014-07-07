#!/usr/bin/env python

from sbl2py import translate_file


import sys
import argparse
parser = argparse.ArgumentParser(description='Compile Snowball to Python')
parser.add_argument('infile', help='Input file (default STDIN)', nargs='?',
		type=argparse.FileType('r'), default=sys.stdin)
parser.add_argument('outfile', help='Output file (default STDOUT)', nargs='?',
		type=argparse.FileType('w'), default=sys.stdout)
args = parser.parse_args()

args.outfile.write(translate_file(args.infile) + "\n")
