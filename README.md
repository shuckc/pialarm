
# pialarm
This repository contains scripts to speak to the panel over the UART serial ports. The project emultates some of the functionality of Wintex, the Texecom windows-based configuration tool. 

To interface a raspberry Pi to the alarm pannel requires only a couple of resistors, plus a 12-15V DC to 5V DC power adapter. In the [hardware](hardware/) directory you can see how to connect it to the Texecom main board. It it not necessary to buy any IP-communicator or Com300 board to do this.

### Protocol

See captured examples and dissections of the ["simple" protocol](protocol/readme.md) and the [Wintext protocol](protocol/wintex-protocol.md).



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


