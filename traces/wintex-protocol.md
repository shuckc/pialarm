# Wintex captures

    < wintex to pannel
    > reply

### Login exchange
UDL password is 12345678, Elite 24 V4.02.01 is the panel type seen from simple protocol.

    < 03 5a a2
    > 0b 5a 05 01 00 07 09 04 07 01 78
    < 0b 5a 31 32 33 34 35 36 37 38 f6
    > 17 5a 45 6c 69 74 65 20 32 34 20 20 20 20 56 34 2e 30 32 2e 30 31 ec
     Z. E. l. i. t. e.    2. 4              V. 4. .  0. 2. .  0. 1

### Query/response to read values `07 4f ...` ?

    < 07 4f 00 64 9b 10 9a
    > 17 49 00 64 9b 10 2f fc 56 50 85 90 48 44 76 11 43 39 ce c4 19 76 fa
    < 07 4f 00 5d 04 10 38
    > 17 49 00 5d 04 10 54 01 07 94 71 b6 49 17 a5 1b 32 5a 96 f9 6e 49 25
    < 07 4f 00 16 78 01 1a
    > 08 49 00 16 78 01 06 19
    < 07 4f 00 1f ca 07 b9
    > 0e 49 00 1f ca 07 01 00 00 00 ff ff 2c 8d
    < 07 4f 00 16 7e 01 14
    > 08 49 00 16 7e 01 00 19
    < 07 4f 00 5c 55 02 f6
    > 09 49 00 5c 55 02 f0 59 b1

### Framing
Looks like length prefixed byte, and from last-digit only
differences between request and response, looks like 1-byte checksum

Sample CRC codes `< 03 5a a2`

    03  0000 0011
    5a  0101 1010
    a2  1010 0010

    07 4f 00 64 9b 10 9a

Doesn't look like XOR based.
Look for plaintext with single bit differences between messages:

    $ less tr1 | grep "07 4f" | cut -c 26- | sort -u | uniq
    07 4f 00 20 00 40 49     |.O. .@I|
    07 4f 00 20 40 40 09     |.O. @@.|  adding 40 subtracts 40 from checksum
    ...
    07 4f 00 2b 80 40 be     |.O.+.@.|
    07 4f 00 2b c0 40 7e     |.O.+.@~|  8->c changes b->7
    ..
    07 4f 00 20 80 40 c9     |.O. .@.|
    07 4f 00 20 c0 40 89     |.O. .@.|  8->c changes c->8

Both cases no cascade of changes to other nibble
Looks like subtractions or 2s compliment addition, bytewise
Possible bias or initial value?

    b8 + 5a = a2
    03 - 5a = a9
    0 - 03 -5a = a3
    FF - 03 - 5a = a2  <-- looks good

    FF - 07 -4f -20 - 40 = 49

To verify substract checksum and look for `(x & 0xFF) = 0`
To encode do FF - each byte value then mask 0xFF

First digit is length of message 0-255 bytes, including check digit and size byte. size byte is included in checksum also.

### Ping/pong when idle
Looks like 10-second timer, client initiates and panel responds

    2018/07/23 12:46:12 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:12 term 05 50 ff ff ac           |.P...|
    2018/07/23 12:46:22 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:22 term 05 50 ff ff ac           |.P...|
    2018/07/23 12:46:32 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:32 term 05 50 ff ff ac           |.P...|
    2018/07/23 12:46:42 tcp  03 50 ac                 |.P.|
    2018/07/23 12:46:42 term 05 50 ff ff ac           |.P...|

### Using virtual keypad feature


Command R is answered by W and seems to be screen polling feature of remote keypad system. Unknown what bytes `00 11 96 22` do but they are returned on the answer.

    2018/07/24 12:46:50 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:50 term 29 57 00 11 96 22 20 53  |)W..." S|
    2018/07/24 12:46:50 term 79 73 74 65 6d 20 41 6c  |ystem Al|
    2018/07/24 12:46:50 term 65 72 74 73 21 20 31 33  |erts! 13|
    2018/07/24 12:46:50 term 3a 34 34 2e 33 37 20 54  |:44.37 T|
    2018/07/24 12:46:50 term 75 65 20 32 34 20 00 00  |ue 24 ..|
    2018/07/24 12:46:50 term b3                       |.|
    2018/07/24 12:46:50 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:50 term 29 57 00 11 96 22 20 53  |)W..." S|
    2018/07/24 12:46:50 term 79 73 74 65 6d 20 41 6c  |ystem Al|
    2018/07/24 12:46:50 term 65 72 74 73 21 20 31 33  |erts! 13|
    2018/07/24 12:46:50 term 3a 34 34 2e 33 38 20 54  |:44.38 T|
    2018/07/24 12:46:50 term 75 65 20 32 34 20 00 00  |ue 24 ..|
    2018/07/24 12:46:50 term b2                       |.|
    2018/07/24 12:46:51 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:51 term 29 57 00 11 96 22 20 53  |)W..." S|
    2018/07/24 12:46:51 term 79 73 74 65 6d 20 41 6c  |ystem Al|
    2018/07/24 12:46:51 term 65 72 74 73 21 20 31 33  |erts! 13|
    2018/07/24 12:46:51 term 3a 34 34 2e 33 38 20 54  |:44.38 T|
    2018/07/24 12:46:51 term 75 65 20 32 34 20 00 00  |ue 24 ..|
    2018/07/24 12:46:51 term b2                       |.|

I sent user login of `5678` which seems to be `4b` K messages acked by `06` (stripping screen polling out):

    2018/07/24 12:46:52 tcp  05 4b 01 05 a9           |.K...|
    2018/07/24 12:46:52 term 03 06 f6                 |...|
    ...
    2018/07/24 12:46:52 tcp  05 4b 01 06 a8           |.K...|
    2018/07/24 12:46:52 term 03 06 f6                 |...|
    ...
    2018/07/24 12:46:53 tcp  05 4b 01 07 a7           |.K...|
    2018/07/24 12:46:53 term 03 06 f6                 |...|
    ...
    2018/07/24 12:46:54 tcp  05 4b 01 08 a6           |.K...|
    2018/07/24 12:46:54 term 03 06 f6                 |...|
    2018/07/24 12:46:54 tcp  07 52 00 11 96 22 dd     |.R...".|
    2018/07/24 12:46:54 term 29 57 00 11 96 22 5a 6f  |)W..."Zo|
    2018/07/24 12:46:54 term 6e 65 20 30 30 31 20 54  |ne 001 T|
    2018/07/24 12:46:54 term 61 6d 70 65 72 20 5a 4f  |amper ZO|
    2018/07/24 12:46:54 term 4d 45 30 30 31 61 62 63  |ME001abc|
    2018/07/24 12:46:54 term 64 65 66 67 68 69 00 00  |defghi..|
    2018/07/24 12:46:54 term 67                       |g|


### Message Types

First payload byte seems to be message type

R seems to be answered by W, O answered by I,
P answers P, Z with Z

    4f  O  options / parameters request
    49  I  parameters response
    50  P  ping/pong heartbeat
    5a  Z  authentication
    52  R  screen request
    57  W  screen reply
    4b  K  keypad press
    06  .  keypad ack


### Funny R/W cycle
Sometimes R/W is not giving back screen messages. Could be another bus device or something else?  `52 00 11 92 22` keypad
 vs. `52 00 1d f8 40` is this:

    2018/07/23 12:50:45 tcp  07 52 00 1d f8 40 51     |.R...@Q|
    2018/07/23 12:50:45 term 47 57 00 1d f8 40 00 00  |GW...@..|
    2018/07/23 12:50:45 term 00 00 00 00 00 ff ff ff  |........|
    2018/07/23 12:50:45 term ff 00 00 00 00 00 00 00  |........|
    2018/07/23 12:50:45 term 00 00 00 00 ff ff ff ff  |........|
    2018/07/23 12:50:45 term 00 00 00 00 00 00 00 00  |........|
    2018/07/23 12:50:45 term 00 00 00 ff ff ff ff 00  |........|
    2018/07/23 12:50:45 term 00 00 00 00 00 00 00 00  |........|
    2018/07/23 12:50:45 term 00 00 ff ff ff ff 00 00  |........|
    2018/07/23 12:50:45 term 00 00 00 00 00 00 1c     |.......|

If I is sent from wintex to the pannel, it always seems to be a block and answered by 0x06, fixed length ack? I think this is pushing configuration.

    2018/07/24 12:43:27 tcp  47 49 00 12 70 40 ff ff  |GI..p@..|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ff ff  |........|
    2018/07/24 12:43:27 tcp  ff ff ff ff ff ff ed     |.......|
    2018/07/24 12:43:28 term 03 06 f6                 |...|
