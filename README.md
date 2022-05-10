
# pialarm
This repository contains scripts to speak to (and impersonate) a Texecom alarm panel over the UART serial and TCP ports. The project emultates some of the functionality of Wintex, the Texecom windows-based configuration tool.

## Running a virtual panel

1. Install Wintex (on linux works well with playonlinux wrapper)
2. Setup a new 'Account' with these settings:

        Panel type:        Elite 24
        Software version:  4.x
        UDL password:      1234
        Network details:   127.0.0.1  port 10001

3. start `udl-server.py` running:

        $ python udl-server.py
        Panel type 'Elite 24    V4.02.01' with UDL password 1234 backed by file /home/chris/alarmpanel.cfg
        Serving UDL on ('::', 10001, 0, 0), ('0.0.0.0', 10001)
        Serving web interface on 10002
        (eval) >

4. In wintex hit `Connect` -> `Connect via. Network (127.0.0.1 on Port 10001)`. Wintex will prompt to reset the fake pannel. You will see some output like:

        udl_server 0: connected
        Sending login prompt
        Recieved UDL login [49, 50, 51, 52]. Sending panel identification
        Configuration read addr=00649b sz=10 data=0x2f,0xfc,0x56,0x50,0x85,0x90,0x48,0x44,0x76,0x11,0x43,0x39,0xce,0xc4,0x19,0x76
        Configuration read addr=005d04 sz=10 data=0x57,0x1,0x7,0x94,0x71,0x49,0x45,0x5,0x9f,0xea,0x6c,0xe7,0xe7,0x1b,0xa8,0x64
        Configuration read addr=001678 sz=1 data=0x0
        Configuration read addr=001fca sz=7 data=0x0,0x0,0x0,0x0,0x0,0x0,0x0
        Configuration read addr=00167e sz=1 data=0x0
        Configuration read addr=005c55 sz=2 data=0x0,0x0
        (eval) >

5. Open up a web browser to `http://localhost:10002` to see the decoded panel configuration

![Web screenshot](./site/screenshot.png)

## Serial connection

To interface a raspberry Pi to the alarm pannel requires only a couple of resistors, plus a 12-15V DC to 5V DC power adapter. In the [hardware](hardware/) directory you can see how to connect it to the Texecom main board. It it not necessary to buy any IP-communicator or Com300 board to do this.


### Protocol

See captured examples and dissections of the ["simple" protocol](protocol/readme.md) and the [Wintex protocol](protocol/wintex-protocol.md).



### Panel configuration

Configure via. the keypad as follows:

    COM1                        configure as 'Not connected'
    COM2                        configure as 'Crestron System'
    COM2 Speed 19200 baud
    COM3                        configure as 'Communicator 300'
    UDL Password -> 12345678    set this in ~/.pialarm





### Preparing the pi
Install a blank `rasbian` install to an SD Card (ideally skipping NOOBS). Boot using a keyboard and screen, then use `sudo raspi-config` to enable ssh (`5 Interfacing Options` -> `P2 SSH` -> `Yes`) then change the password for the `pi` user using `passwd`.

It is necessary to disable the serial `tty` that raspian attaches to `/dev/ttyACM0` in order to access the hardware UART. With recent rasbian releases it is a simple matter of running `sudo raspi-config` and disabling the serial tty under `5 Interfacing Options` -> `P6 Serial` -> `No` -> `Yes` -> `OK`, giving this summary:

    The serial login shell is disabled
    The serial interface is enabled

Now install the contents of this repository to `~/pialarm` as follows:

	$ sudo apt-get install git
    $ git clone https://github.com/shuckc/pialarm.git
    $ cd pialarm
    $ pip3.6 install -r requirements.txt
    $ python

You may also update the Pi kernel and firmware with `$ sudo rpi-update` - didn't cause any problems for me.



### Wiring
First I used a couple of FTDI USB external COM ports (5V tolerant) as a proof of concept. However it is much neater to omit these and use the GPIO pins on the pi directly. The COM ports on the alarm mainboard all drive `Tx` to 5V logic levels, with a series protection resistor of 9.1kOhm, which needs to be accounted for in the voltage divider to reduce to 3.3V logic for the raspberry pi GPIO pins. Since the protection resistor is quite large, I used this as the top resister in the divider chain, with a bottom resistor of 15kOhm. For Rpi -> Panel, I drove the panel's Rx pin directory with no problems.

For more details see [hardware](hardware/).

### Legal
This project is not affiliated with Texecom. The protocols were reversed engineered using a Salae Logic8 logic probe, and later by capturing traffic using the `ser2net` tool, and custom scripts to convert trace files to memory maps. See the [protocol](protocol/) directory for these. For the fine details, a panel was emulated with `udl-server.py` and WinTex used to change settings individually. No author or contributor has signed the Texecom NDA agreement.

If you use the configuration system to change panel settings, this is done at your own risk. It is not beyond the realm of possibility that a panel might need NVM reset to recover or the use of a firmware flasher.

### See also

* Mike Stirling's @mikestir  implementation of an [Alarm Receiving Centre ARC](https://github.com/mikestir/alarm-server ), expecting messages over TCP, so requires e.g. ComIP communicator module
* @kieranmjones who first freely documented the [Cestron protocol](https://github.com/kieranmjones/homebridge-texecom/blob/master/index.js )
* @stuartyio who runs the Selfmon site for Honeywell panels
* Nexmo [text-to-speech](https://developer.nexmo.com/voice/voice-api/guides/text-to-speech) a very reliable and low cost way to send calls and SMS messages over IP
* [Telegram bot API](https://core.telegram.org/bots/api) for sending events to a chat group that can be setup on mobile phones.
* Gw0udm's [blog](https://gw0udm.wordpress.com/category/texecom/) which details serial port connectivity information as well as COM3 and various communicator systems.
* [Leo Crawford's brute forcing](https://www.leocrawford.org.uk/2019/01/10/brute-forcing-my-own-texecom-premier-elite.html) of the UDL login.
* RoganDawes' [ESPHome_Wintex](https://github.com/RoganDawes/ESPHome_Wintex) which can bridge Zone status to Home Assistant.
* RoganDawes' [Java WintexProtocol](https://github.com/RoganDawes/WintexProtocol) decoder
