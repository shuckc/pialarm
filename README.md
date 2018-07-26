
# pialarm
Have a Texecom Premier alarm panel? This repository contains scripts and a webserver to speak to the panel over the UART serial ports, ideally from a raspberry pi computer within the alarm panel itself, to provide remote monitoring and alarm escalation over the internet.

The project emultates some of the functionality of Wintex, the Texecom windows-based configuration system, and also uses parts of the Cestron protocol for real-time event monitoring. It will also speak the monitoring protocol to allow the panel to monitor the uptime of the raspberry pi and communicate alarms.

To interface a raspberry Pi to the alarm pannel requires only a couple of resistors, plus a 12-15V DC to 5V DC power adapter. in the hardware directory you will find a small shield fitting the GPIO header to do this, and instructions to connect it to the Texecom main board. It it not necessary to buy any IP-communicator or Com300 board to do this.

### Panel configuration
Configure via. the keypad as follows:

    COM1                        configure as 'Not connected'
    COM2                        configure as 'Cestron'
    COM2 Speed 19200 baud
    COM3                        configure as 'Communicator 300'
    UDL Password -> 12345678    set this in ~/.pialarm

### Preparing the pi
Install a blank `rasbian` install to an SD Card (ideally skipping NOOBS). Boot using a keyboard and screen, then use `sudo raspi-config` to enable ssh (`5 Interfacing Options` -> `P2 SSH` -> `Yes`) then change the password for the `pi` user using `passwd`.

It is necessary to diable the serial `tty` that raspian attaches to `/dev/ttyACM0` in order to have this working. Instructions to do this can be found online, it is a simple matter of running `sudo raspi-config` and disabling the serial tty under `5 Interfacing Options` -> `P6 Serial` -> `No` -> `Yes` -> `OK`, giving this summary:

    The serial login shell is disabled
    The serial interface is enabled

Now install the contents of this repository to `~/pialarm` as follows:

	$ sudo apt-get install git
    $ git clone https://github.com/shuckc/pialarm.git

You may also update the Pi kernel and firmware with `$ sudo rpi-update` - didn't cause any problems for me.

### Wiring
First I used a couple of FTDI USB external COM ports (5V tolerant) as a proof of concept. However it is much neater to omit these and use the GPIO pins on the pi directly. The COM ports on the alarm mainboard all drive `Tx` to 5V logic levels, with a series protection resistor of 9.1kOhm, which needs to be accounted for in the voltage divider to reduce to 3.3V logic for the raspberry pi GPIO pins. Since the protection resistor is quite large, I used this as the top resister in the divider chain, with a bottom resistor of 15kOhm. For Rpi -> Pannel, I drove the panel's Rx pin directory with no problems.

For more details see [hardware](hardware/).

### Legal
The protocols were reversed engineered using a Salae Logic8 logic probe, and later by capturing traffic using the `ser2net` tool. See the [traces](traces/) directory for these. No author or contributor has signed the Texecom NDA agreement.


