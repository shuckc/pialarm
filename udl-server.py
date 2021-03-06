import argparse
import trio
from itertools import count
from trace2op import SerialWintex, MemStore

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--verbose", help="Print instructions", action='store_true', default=False)
parser.add_argument("--debug", help="Print bytes on wire", action='store_true', default=False)
parser.add_argument("--mem", help="write observed values to MEMFILE in position")

PORT = 10001
# How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# but shouldn't be too big or too small.
BUFSIZE = 16384
CONNECTION_COUNTER = count()

ACK_MSG = [ 0x06 ]
class SerialWintexPanel(SerialWintex):
    def handle_msg(self, mtype, body):
        # commands we will store and destination region

        if mtype == 'Z' and len(body) == 0:
            print('Sending login prompt')
            return self.prep('Z\x05\x01\x00\x07\x09\x04\x07\x01')
        elif mtype == 'Z':
            print('Sending panel identification')
            return self.prep('ZElite 24    V4.02.01')
        # wintex shows 'Reading UDL options'
        elif mtype == 'O': # configuration read
            base = (body[0] << 16) + (body[1] << 8) + body[2]
            sz = body[3]
            print('Configuration read addr={:06x} sz={:01x}'.format(base, sz))
            data = self.mem[base:base+sz]
            return [ord('I')] + body[0:4] + list(data) # echo back addr and sz
        elif mtype == 'I': # configuration write
            base = (body[0] << 16) + (body[1] << 8) + body[2]
            sz = body[3]
            if sz + 4 != len(body):
                raise Exception('config write length mismatch')
            old_data = self.mem[base:base+sz]
            self.mem[base] = body[4:]
            data = self.mem[base:base+sz]
            self.print_deltas(base, old_data, data)
            return ACK_MSG
        elif mtype == 'R': # live state read
            base = (body[0] << 16) + (body[1] << 8) + body[2]
            sz = body[3]
            print('Live state read addr={:06x} sz={:01x}'.format(base, sz))
            data = self.io[base:base+sz]
            return [ord('W')] + body[0:4] + list(data)
        elif mtype == 'P': # Heartbeat
            return [ord('P'), 255, 255]
        elif mtype == 'U': # Special action?
            # U 01 - commit zone, expander changes
            if body[0] == 1:
                print('Committing zone changes?')
                return ACK_MSG
            else:
                raise Exception('Unknown special action {} with args {!r}'.format(mtype, body))
        else:
            raise Exception('Unknown command {} with args {!r}'.format(mtype, body))

    def print_deltas(self, base, old, new):
        if old != new:
            for n,(i,j) in enumerate(zip(old, new)):
                if i != j:
                    print('  mem: updated {:06x} old={:02x} new={:02x}'.format(base+n, i, j))

    def prep(self, msg):
        return [ ord(x) for x in msg]

async def udl_server(mem, io, args, server_stream):
    # Assign each connection a unique number to make our debug prints easier
    # to understand when there are multiple simultaneous connections.
    ser = SerialWintexPanel(args, 'tcp', mem=mem, io=io)
    ident = next(CONNECTION_COUNTER)
    print("udl_server {}: started".format(ident))
    try:
        while True:
            data = await server_stream.receive_some(BUFSIZE)
            if args.debug:
                print("udl_server {}: received data {!r}".format(ident, data))

            if not data:
                print("udl_server {}: connection closed".format(ident))
                return

            for reply in ser.on_bytes(data):
                reply = bytes(reply)
                if args.debug:
                    print(' udl_server {}: sending {}'.format(ident, reply))
                await server_stream.send_all(reply)

    # FIXME: add discussion of MultiErrors to the tutorial, and use
    # MultiError.catch here. (Not important in this case, but important if the
    # server code uses nurseries internally.)
    except Exception as exc:
        # Unhandled exceptions will propagate into our parent and take
        # down the whole program. If the exception is KeyboardInterrupt,
        # that's what we want, but otherwise maybe not...
        print("udl_server {}: crashed: {!r}".format(ident, exc))
        raise

async def main():
    args = parser.parse_args()

    with MemStore(args.mem, size=0x8000, file_offset=0x0) as wr_mem, MemStore(args.mem, size=0x4000, file_offset=0x8000) as wr_io:
        async def instance(server_stream):
            await udl_server(wr_mem, wr_io, args, server_stream)
        await trio.serve_tcp(instance, PORT)

# We could also just write 'trio.run(serve_tcp, echo_server, PORT)', but real
# programs almost always end up doing other stuff too and then we'd have to go
# back and factor it out into a separate function anyway. So it's simplest to
# just make it a standalone function from the beginning.
trio.run(main)
