#!/usr/bin/env python

import argparse
import asyncio
from itertools import count
from pialarm import SerialWintex, MemStore
from functools import partial

from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("--panel", help="Specify the panel to identify as\nUse 'Premier 832 V4.0' for an 832", default='Elite 24    V4.02.01')
parser.add_argument("--verbose", help="Print instructions", action='store_true', default=False)
parser.add_argument("--debug", help="Print bytes on wire", action='store_true', default=False)
parser.add_argument("--mem", help="write observed values to MEMFILE in position")

PORT = 10001
# How much memory to spend (at most) on each call to recv. Pretty arbitrary,
# but shouldn't be too big or too small.
BUFSIZE = 16384
CONNECTION_COUNTER = count()

ACK_MSG = [ 0x06 ]

KEY_MAP = {
    0x01: 'Digit 1', 0x02: 'Digit 2', 0x03: 'Digit 3', 0x04: 'Digit 4', 0x05: 'Digit 5',
    0x06: 'Digit 6', 0x07: 'Digit 7', 0x08: 'Digit 8', 0x09: 'Digit 9', 0x0a: 'Digit 0',
    0x0b: 'Omit', 0x0c: 'Menu', 0x0d: 'Yes', 0x0e: 'Part', 0x0f: 'No',
    0x10: 'Area', 0x14: 'Chime', 0x15: 'Reset', 0x16: 'Up', 0x17: 'Down',
}

def unpack_mem_proto(region, msg_body):
    base = (msg_body[0] << 16) + (msg_body[1] << 8) + msg_body[2]
    sz = msg_body[3]
    if not len(msg_body) in [4, sz+4]:
        raise Exception('config read/write length {} vs. data payload {} mismatch'.format(sz, len(msg_body)))
    old_data = region[base:base+sz]
    wr_data = msg_body[4:]
    return (base, sz, wr_data, old_data)

class SerialWintexPanel(SerialWintex):
    def handle_msg(self, mtype, body):
        # commands we will store and destination region

        if mtype == 'Z' and len(body) == 0:
            print('Sending login prompt')
            return self.prep('Z\x05\x01\x00\x07\x09\x04\x07\x01')
        elif mtype == 'Z':
            print('Sending panel identification')
            return self.prep('Z' + self.args.panel)
        elif mtype == 'H':
            print('Wintex hang up')
            return [ 0x03, 0x06, 0xF6 ]
        # wintex shows 'Reading UDL options'
        elif mtype == 'O': # configuration read
            base, sz, wr_data, old_data = unpack_mem_proto(self.mem, body)
            print('Configuration read addr={:06x} sz={:01x} data={}'.format(base, sz, ','.join(hex(x) for x in old_data)))
            return [ord('I')] + body[0:4] + list(old_data) # echo back addr and sz
        elif mtype == 'I': # configuration write
            base, sz, wr_data, old_data = unpack_mem_proto(self.mem, body)
            self.print_deltas(base, old_data, wr_data)
            self.mem[base] = wr_data
            return ACK_MSG
        elif mtype == 'R': # live state read
            base, sz, wr_data, old_data = unpack_mem_proto(self.io, body)
            print('Live state read addr={:06x} sz={:01x} data={}'.format(base, sz, ','.join(hex(x) for x in old_data)))
            return [ord('W')] + body[0:4] + list(old_data)
        elif mtype == 'W': # live state write
            base, sz, wr_data, old_data = unpack_mem_proto(self.io, body)
            print('Live state write addr={:06x} sz={:01x}'.format(base, sz))
            self.print_deltas(base, old_data, wr_data)
            self.io[base] = wr_data
            return ACK_MSG
        elif mtype == 'P': # Heartbeat
            return [ord('P'), 255, 255]
        elif mtype == 'K': # Keypad press
            print('Keypad {} pressed 0x{:02x} - {}'.format(body[0], body[1], KEY_MAP.get(body[1])))
            return ACK_MSG
        elif mtype == 'U': # Special action?
            # U 01 - commit zone, expander changes
            if body[0] == 1:
                print('Committing zone changes?')
                return ACK_MSG
            elif body[0] == 64:
                print('Sending message to keypads')
                return ACK_MSG
            else:
                print('Unknown U special action {} with args {!r}'.format(mtype, body))
        elif mtype == 'A':
            print('Arming area {}'.format(body[0]))
            return ACK_MSG
        elif mtype == 'C':
            print('Resetting area {}'.format(body[0]))
            return ACK_MSG
        elif mtype == 'S':
            print('Part arming area {} type={}'.format(body[0], body[1]))
            return ACK_MSG
        elif mtype == 'B':
            # RTC programming done via. B with args [56, 9, 29, 1, 0]
            if body == [56, 9, 29, 1, 0]:
                print('RTC initialise special op 1')
                return ACK_MSG
            elif body == [57, 9, 29, 1, 0]:
                print('RTC initialise special op 2')
                return ACK_MSG
            else:
                raise Exception('Unknown B special action {} with args {!r}'.format(mtype, body))
        else:
            print('Unknown command {} with args {!r}'.format(mtype, body))

    def print_deltas(self, base, old, new):
        if old != new:
            for n,(i,j) in enumerate(zip(old, new)):
                if i != j:
                    print('  mem: updated {:06x} old={:02x} new={:02x}'.format(base+n, i, j))

    def prep(self, msg):
        return [ ord(x) for x in msg]

async def udl_server(mem, io, args, reader, writer):
    # Assign each connection a unique number to make our debug prints easier
    # to understand when there are multiple simultaneous connections.
    ser = SerialWintexPanel(args, 'tcp', mem=mem, io=io)
    ident = next(CONNECTION_COUNTER)
    print("udl_server {}: started".format(ident))
    try:
        while True:
            data = await reader.read(BUFSIZE)
            if args.debug:
                print("udl_server {}: received data {!r}".format(ident, data))

            if not data:
                print("udl_server {}: connection closed".format(ident))
                return

            for reply in ser.on_bytes(data):
                reply = bytes(reply)
                if args.debug:
                    print(' udl_server {}: sending {}'.format(ident, reply))
                writer.write(reply)

    except Exception as exc:
        # Unhandled exceptions will propagate into our parent and take
        # down the whole program. If the exception is KeyboardInterrupt,
        # that's what we want, but otherwise maybe not...
        print("udl_server {}: crashed: {!r}".format(ident, exc))
        raise

async def handle_wintex(reader, writer):
    pass

async def serve_tcp(handler, address="127.0.0.1", port=10001):
    server = await asyncio.start_server(
        handler, address, port)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    try:
        async with server:
            await server.serve_forever()
    except asyncio.exceptions.CancelledError:
        pass

async def interactive_shell(mem, io):
    """
    Provides a simple repl that allows interactive
    modification of the panel memory.
    """
    # Create Prompt.
    session = PromptSession("(eval) > ")

    # Run echo loop. Read text from stdin, and reply it back.
    while True:
        try:
            input = await session.prompt_async()
            exec(input)
        except (EOFError, KeyboardInterrupt):
            return
        except Exception as ex:
            print(str(ex))

async def main():
    args = parser.parse_args()

    with patch_stdout():
        with MemStore(args.mem, size=0x8000, file_offset=0x0) as mem, MemStore(args.mem, size=0x4000, file_offset=0x8000) as io:

            async def socket_handler(reader, writer):
                await udl_server(mem, io, args, reader, writer)
            panel_task = asyncio.create_task(serve_tcp(socket_handler, "", PORT))
            try:
                await interactive_shell(mem, io)
            finally:
                panel_task.cancel()
            print("Quitting event loop. Bye.")

asyncio.run(main())
