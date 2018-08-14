import argparse
import sys
import array
import json

# reads a ser2net trace files from stdin and prints the high-level operations.
# Optionally writes the implied contents of panel mamory to MEMFILE
# verifies serial checksums in the trace
# e.g. $ cat traces/wintex-ser2net/*.trace | python3.6 trace2op.py --mem blob.mem

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", help="Print instructions", action='store_true', default=False)
parser.add_argument("--debug", help="Print bytes on wire", action='store_true', default=False)
parser.add_argument("--trace", help="Read from file", default='-')
parser.add_argument("--mem", help="write observed values to MEMFILE in position")



def printable(c, alt=None): # c should be int 0..255
	if alt is None:
		alt = '0x{:02x}'.format(c)
	return chr(c) if str.isprintable(chr(c)) else alt

class SerialWintex():
	def __init__(self, args, direction, mem=None, io=None):
		self.buf = []
		self.args = args
		self.direction = direction
		self.mem = mem
		self.io = io
	def on_bytes(self, bytes_message, context=None):
		self.buf.extend(bytes_message)
		if self.args.debug:
			print(" buffer: {:4s} {}".format(self.direction, self.buf))
		# have we a full message in this direction
		while len(self.buf) > 0 and len(self.buf) >= self.buf[0]:
			sz = self.buf[0]
			chk = self.checksum(self.buf[0:sz])
			if chk != 0:
				print("Warning: bad checksum for {} at {} -> {}, emptying buffer".format(self.direction, context,  self.buf, chk))
				del self.buf[:]
			else:
				reply = self.parse_msg(self.buf[1:sz-1]) # parser does not need length or checksum
				if reply:
					reply.insert(0, len(reply)+2) # prepend size, len(msg)+chk+sz
					checksum = self.checksum(reply)
					reply.append(checksum)
					yield reply
				del self.buf[0:sz]
		return
	def checksum(self, msg):
		# subtract each byte from 0xff
		v = 255
		for b in msg:
			v -= b
		return v % 256

	def log_msg(self, direction, msg):
		mtype = msg[0]
		printable_type = printable(mtype)
		msg_hex = ' '.join('{:02x}'.format(m) for m in msg[1:])
		msg_ascii = ''.join(printable(c, alt='.') for c in msg[1:])
		if self.args.verbose:
			print("  {:4s} {} {} | {} ".format(direction, printable_type, msg_hex, msg_ascii))

	def parse_msg(self, msg):
		self.log_msg('<', msg)
		mtype = msg[0]
		printable_type = printable(mtype)
		reply = self.handle_msg(printable_type, msg[1:])
		if reply:
			self.log_msg('>', reply)
		return reply

	def handle_msg(self, mtype, body):
		pass

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


class WintexMemDecoder():
	def __init__(self, mem, io):
		# Probably these can be determined from the panel type. These work for
		# a Premier Elite 24
		self.zones = 24
		self.users = 25
		self.expanders = 2
		self.keypads = 4
		self.areas = 2
		self.mem = mem
		self.io = io

	def get_ascii(self, mem, start, sz):
		rgn = mem[start:start+sz]
		return ''.join([chr(x) for x in rgn])

	def get_bcd(self, mem, start, sz):
		rgn = mem[start:start+sz]
		return ''.join(['{:02x}'.format(x) for x in rgn])

	def decode(self):
		js = {}
		js['zones'] = self.decode_zones()
		js['users'] = self.decode_users()
		js['areas'] = self.decode_areas()
		js['config'] = {
			'unique_id': self.get_bcd(self.mem, 0x005d04,0x10),
			'engineer_reset': self.get_ascii(self.mem, 0x001100, 32),
			'anticode_reset': self.get_ascii(self.mem, 0x001120, 32),
			'service_message': self.get_ascii(self.mem, 0x001140, 32),
			'panel_location': self.get_ascii(self.mem, 0x001160, 32),
			'banner_message': self.get_ascii(self.mem, 0x001180, 16),
 			'part_arm_header': self.get_ascii(self.mem, 0x001190, 16),
			'part_arm1_message': self.get_ascii(self.mem, 0x001800, 16),
			'part_arm2_message': self.get_ascii(self.mem, 0x001810, 16),
			'part_arm3_message': self.get_ascii(self.mem, 0x001820, 16),
			}
		js['area_suites'] = self.decode_area_suites()
		js['expanders'] = self.decode_expanders()
		js['enums'] = {
			'zones.type': {
				'type': 'lookup',
				'key': 'int1',
				'values': ['Entry/Exit 1', 'Entry/Exit 2', 'Guard', 'Guard Access', '24hr Audible', '24hr Silent', 'PA Audible', 'PA Silent', 'Fire', 'Medical', '24hr Gas', 'Auxilary', 'Tamper', 'Exit Terminator', 'Moment Key', 'Latch Key', 'Security', 'Omit Key', 'Custom', 'Conf PA Audible', 'Conf PA Silent'],
			},
			'zones.wiring': {
				'type': 'lookup',
				'key': 'int0',
				'values': ['Normally Closed', 'Normally Open', 'Double Pole/EOL', 'Tripple EOL', '1K/1K/(3K)', '4K7/6K8/(12K)', '2K2/4K7/(6K8)', '4K7/4K7', 'WD Monitor'],
			},
			'zones.access_areas': {
				'type': 'bitmask',
				'values': ['A', 'B'],
			},
			'keypad.leds': {
				'type': 'bitmask',
				'values': [ '?', '?', 'Omit'],
			}
		}
		js['communications'] = {
			'sms_centre1': self.get_ascii(self.mem, 0x001a30, 16),
			'sms_centre2': self.get_ascii(self.mem, 0x001a40, 16),
		}
		js['keypad'] = {
			'screen': self.get_ascii(self.io, 0x001196, 16),
			'screen2': self.get_ascii(self.io, 0x0011A6, 16),
			'leds': self.io[0x11B7],
		}
		return js

	def decode_users(self):
		users = []
		# merge pincode buffers
		pincode = array.array('B', self.mem[0x004190:0x004190+0x4b])
		pincode.extend(self.mem[0x00630b:0x00630b+0x18])
		for i in range(self.users):
			users.append({
				'name': self.get_ascii(self.mem, 0x004000+8*i, 8).rstrip(),
				'pincode': self.get_pincode(pincode, 3*i),
				'access_areas': self.mem[0x0042ee+i*2],
				'flags0': '{:02x}'.format(self.mem[0x0042b6+i]),
				'flags1': '{:02x}'.format(self.mem[0x0043e8+i])
			})
		return users

	def decode_zones(self):
		zones = []
		for i in range(self.zones):
			zones.append({
				'name': self.get_ascii(self.mem, 0x005400+i*32, 16),
				'name2': self.get_ascii(self.mem, 0x005400+i*32+16, 16),
				'type': self.mem[0+i],
				'flags': self.mem[0x000030+i],
				'area': self.mem[0x000060+i],
				'wiring': self.mem[0x000090+i],

			})
		return zones

	def decode_areas(self):
		areas = []
		for i in range(self.areas):
			areas.append({
				'text': self.get_ascii(self.mem, 0x0016a0+i*16, 16),
			})
		return areas
	def decode_expanders(self):
		expanders = []
		for i in range(self.expanders):
			expanders.append({
				'location': self.get_ascii(self.mem, 0x000e50+i*16,16),
			})
		return expanders

	def decode_area_suites(self):
		suites = []
		for i in range(2):
			suites.append({
				'id': i,
				'text': self.get_ascii(self.mem, 0x0005e8+i*16, 16),
				'arm_mode': '',
				'areas': '',
				})
		return suites

	def get_pincode(self, mem, offset):
		x = mem[offset:offset+3].tolist()
		return '{:x}{:x}{:x}'.format(*x).strip('def')

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



