import argparse
import sys
import array

# reads a ser2net trace files from stdin and prints the high-level operations.
# Optionally writes the implied contents of panel mamory to MEMFILE
# verifies serial checksums in the trace
# e.g. $ cat traces/wintex-ser2net/*.trace | python3.6 trace2op.py --mem blob.mem

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", help="Print instructions", action='store_true', default=False)
parser.add_argument("--debug", help="Print bytes on wire", action='store_true', default=False)
parser.add_argument("--trace", help="Read from file", default='-')
parser.add_argument("--mem", help="write observed values to MEMFILE in position")

def checksum(msg):
	# subtract each byte from 0xff
	v = 255
	for b in msg:
		v -= b
	return v % 256

def printable(c, alt=None): # c should be int 0..255
	if alt is None:
		alt = '0x{:02x}'.format(c)
	return chr(c) if str.isprintable(chr(c)) else alt

def parse(args, dir, msg, mem, io):
	mtype = msg[0]
	printable_type = printable(mtype)
	msg_hex = ' '.join('{:02x}'.format(m) for m in msg[1:])
	msg_ascii = ''.join(printable(c, alt='.') for c in msg[1:])
	if args.verbose:
		print("  {:4s} {} {} | {} ".format(direction, printable_type, msg_hex, msg_ascii))

	# commands we will store and destination region
	parts = { ('term', 'I'): mem, ('term', 'W'): io }
	c = parts.get( (direction, printable_type), None)
	if c:
		base = (msg[1] << 16) + (msg[2] << 8) + msg[3]
		sz = msg[4]
		if sz + 5 != len(msg):
			raise Exception("IO length byte does not match msg payload sz")
		c[base] = msg[5:]

class MemStore():
	def __init__(self, filename, size=0x0, file_offset=0x0):
		self.backing_file = None
		self.file_offset = file_offset
		self.size = size
		self.backing_array = array.array('B', [0]*size)
		try:
			if filename == None: raise RuntimeError('not backed by file')
			self.backing_file = open(filename, mode="rb+")
			self.backing_file.seek(file_offset)
			self.backing_array = array.array('B', [])
			self.backing_array.fromfile(self.backing_file, size)
		except FileNotFoundError as e:
			self.backing_file = open(filename, mode="wb+")
		except EOFError as e:
			# file on disk too small, we've also effectively truncated backing_array, oops
			self.backing_array = array.array('B', [0]*size)
		except Exception as e:
			raise e

	def __enter__(self):
		return self
	def __exit__(self, type, value, traceback):
		if self.backing_file:
			print('Writing 0x{:x} bytes to offet 0x{:x} within {}'.format(self.size, self.file_offset, self.backing_file))
			self.backing_file.seek(self.file_offset)
			self.backing_array.tofile(self.backing_file)
			self.backing_file.close()

	def __getitem__(self, key):
		return self.backing_array[key]
	def __setitem__(self, key, value):
		#if key > self.size:
		#	raise IndexError('position {:x} is beyond size={:x}'.format(key, self.size))
		self.backing_array[key:key+len(value)] = array.array('B', value)

if __name__ == '__main__':
	args = parser.parse_args()

	stream = sys.stdin if args.trace == '-' else open(args.trace)

	with MemStore(args.mem, size=0x8000, file_offset=0x0) as wr_mem, MemStore(args.mem, size=0x4000, file_offset=0x8000) as wr_io:

		buffers = {'tcp': [], 'term': []}
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
			buf.extend([int(x,16) for x in hexbytes.split(' ')])
			if args.debug:
				print(" buffer: {:4s} {}".format(direction, buf))
			# have we a full message in this direction
			sz = buf[0]
			if len(buf) >= sz:
				chk = checksum(buf[0:sz])
				if chk != 0:
					print("Warning: bad checksum at {} {} {} -> {}, emptying buffer".format(datetime, direction, buf, chk))
					del buf[:]
				else:
					parse(args, direction, buf[1:sz-1], wr_mem, wr_io) # parser does not need length or checksum
					del buf[0:sz]



