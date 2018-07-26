# pialarm
Hava a Texecom alarm panel? This repository contains scripts and a webserver to speak to the panel over the UART serial ports, ideally from a raspberry pi computer within the alarm pannel itself.

The project emultates some of the functionality of Wintex, the Texecom windows-based configuration system, and also uses parts of the Cestron protocol for real-time event monitoring. It will also speak the monitoring protocol to allow the panel to monitor the uptime of the raspberry pi and communicate alarms.

To interface a raspberry Pi to the alarm pannel requires only a couple of resistors, plus a 12-15V DC to 5V DC power adapter. in the hardware directory you will find a small shield fitting the GPIO header to do this, and instructions to connect it to the Texecom main board. It it not necessary to buy an IP-communicator or GPS model to do this.

The protocols were reversed engineered using a Salae Logic8 logic probe, and later by capturing traffic using the `ser2net` tool. See the `traces` directory for these. No author or contributor has signed the Texecom NDA agreement.
