README
======

This is the official Boson SDK library, as distributed by Flir.

As of late 2017, Flir doesn't actually publish this code anywhere on the
internet, and it's necessary to get the latest updates by contacting them
directly.

BUILDING
========

The Makefile should build a shared library on most Linux OS's.

It has been tested on Ubuntu 14.04.

  $ sudo apt-get install libusb-1.0-0-dev
  $ sudo apt-get install libusb-1.0-0
  $ make
  $ sudo make install
  gcc -shared -o libboson_sdk.so Client_API.o Client_Packager.o flirCRC.o 
                 Serializer_BuiltIn.o UART_Connector.o Client_Dispatcher.o
		 flirChannels.o libusb_binary_protocol.o Serializer_Struct.o
  * Installing shared library to: /usr/local/lib/libboson_sdk.so
  * Installing Boson header file: /usr/local/include/Client_API.h

This will install the shared library into /usr/local/lib and the necessary
header files into /usr/local/include.

To run the example:
  $ make example
  $ ./example

On OSX:

  $ brew install libusb
  $ make
  

AUTHOR
======

Cory Spencer <cory@eiodiagnostics.com>
