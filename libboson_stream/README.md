README
======

A lightweight C library for accessing the Boson's streaming capabilities
based on Video4Linux.

### DEPENDENCIES

This library requires that the OpenCV 3.x libraries and development headers
are installed.

### BUILDING

The Makefile should build a shared library on most Linux OS's.

It has been tested on Ubuntu 14.04.
```
  $ make
  $ sudo make install
  gcc -fPIC -O4 -g -shared -o libboson_stream.so boson_stream.o -lpthread
  * Installing shared library to: /usr/local/lib/libboson_stream.so
  * Installing Boson stream header file: /usr/local/include/boson_stream.h
```
This will install the shared library into /usr/local/lib and the necessary
header files into /usr/local/include.

### Testing

The Python pyboson library has a file called "test.py" which will open a
window using the OpenCV libraries to display a real time view of what the
Boson camera is currently seeing.

Switch to the pyboson project subdirectory, ensure it all its dependencies
are installed, and run the "test.py" script.

### AUTHOR

Cory Spencer <cory@eiodiagnostics.com>
