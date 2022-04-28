import argparse
import sys
import array
import json
from collections.abc import Iterable

from pialarm import SerialWintex, MemStore, WintexMemDecoder

# reads a ser2net trace files from stdin and prints the high-level operations.
# Optionally writes the implied contents of panel mamory to MEMFILE
# verifies serial checksums in the trace
# e.g. $ cat traces/wintex-ser2net/*.trace | python3.6 trace2op.py --mem blob.mem

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", help="Print instructions", action='store_true', default=False)
parser.add_argument("--debug", help="Print bytes on wire", action='store_true', default=False)
parser.add_argument("--trace", help="Read from file", default='-')
parser.add_argument("--mem", help="write observed values to MEMFILE in position")


class SerialWintexRecord(SerialWintex):
	def handle_msg(self, mtype, body):
		# commands we will store and destination region
		parts = { ('term', 'I'): self.mem, ('term', 'W'): self.io }
		c = parts.get( (self.direction, mtype), None)
		if c:
			base = (body[0] << 16) + (body[1] << 8) + body[2]
			sz = body[3]
			if sz + 4 != len(body):
				raise Exception("IO length byte does not match msg payload sz")
			c[base] = body[4:]
		return None

if __name__ == '__main__':
	args = parser.parse_args()

	stream = sys.stdin if args.trace == '-' else open(args.trace)

	with MemStore(args.mem, size=0x8000, file_offset=0x0) as wr_mem, MemStore(args.mem, size=0x4000, file_offset=0x8000) as wr_io:

		buffers = dict([(direction, SerialWintexRecord(args, direction, mem=wr_mem, io=wr_io)) for direction in ['tcp', 'term']])
		for line in stream:
			# 2018/07/31 08:30:59 tcp  03 5a a2                 |.Z.|
			datetime = line[0:19]
			direction = line[20:25].strip()
			if direction not in buffers:
				continue
			hexbytes = line[25:50].strip()
			if args.debug:
				print("in: {}' '{}' {}".format(datetime, direction, hexbytes.split(' ')))
			#decode bytes from hexbytes and push to buffer
			buf = buffers[direction]
			buf.on_bytes([int(x,16) for x in hexbytes.split(' ')], datetime)

		dec = WintexMemDecoder(wr_mem, wr_io)
		print(json.dumps(dec.decode(), indent=4))
