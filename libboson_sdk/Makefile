HEADER_FILES = Client_API.h
SHARED_LIB   = libboson_sdk.so
LLFLAGS 	 = 

INCLUDE_DIR  = /usr/local/include/
LIBRARY_DIR  = /usr/local/lib/

CCFLAGS = -fPIC -ggdb
LDCONFIG     = sudo /sbin/ldconfig

# https://stackoverflow.com/q/714100/54745
# detect OS, adjust flags
ifeq ($(OS),Windows_NT)
    CCFLAGS += -D WIN32
    ifeq ($(PROCESSOR_ARCHITEW6432),AMD64)
        CCFLAGS += -D AMD64
    else
        ifeq ($(PROCESSOR_ARCHITECTURE),AMD64)
            CCFLAGS += -D AMD64
        endif
        ifeq ($(PROCESSOR_ARCHITECTURE),x86)
            CCFLAGS += -D IA32
        endif
    endif
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Linux)
        CCFLAGS += -D LINUX
    endif
    ifeq ($(UNAME_S),Darwin)
        CCFLAGS += -D OSX
        LLFLAGS += $(LIBRARY_DIR)/libusb-1.0.a -lobjc -framework IOKit -framework CoreFoundation
        LDCONFIG     = true
        SHARED_LIB = libboson_sdk.dylib
    endif
    UNAME_P := $(shell uname -p)
    ifeq ($(UNAME_P),x86_64)
        CCFLAGS += -D AMD64
    endif
    ifneq ($(filter %86,$(UNAME_P)),)
        CCFLAGS += -D IA32
    endif
    ifneq ($(filter arm%,$(UNAME_P)),)
        CCFLAGS += -D ARM
    endif
endif


all: libboson_sdk 

libboson_sdk: Client_API.o Client_Packager.o flirCRC.o Serializer_BuiltIn.o UART_Connector.o \
Client_Dispatcher.o flirChannels.o libusb_binary_protocol.o Serializer_Struct.o
	gcc -shared -o $(SHARED_LIB) Client_API.o Client_Packager.o flirCRC.o Serializer_BuiltIn.o \
	UART_Connector.o Client_Dispatcher.o flirChannels.o libusb_binary_protocol.o Serializer_Struct.o \
	$(LLFLAGS)

Client_API.o: Client_API.c Client_API.h
	gcc $(CCFLAGS) -c Client_API.c

Client_Packager.o: Client_Packager.c Client_Packager.h
	gcc $(CCFLAGS) -c Client_Packager.c

flirCRC.o: flirCRC.c flirCRC.h
	gcc $(CCFLAGS) -c flirCRC.c

Serializer_BuiltIn.o: Serializer_BuiltIn.c Serializer_BuiltIn.h
	gcc $(CCFLAGS) -c Serializer_BuiltIn.c

UART_Connector.o: UART_Connector.c UART_Connector.h
	gcc $(CCFLAGS) -c UART_Connector.c

Client_Dispatcher.o: Client_Dispatcher.c Client_Dispatcher.h
	gcc $(CCFLAGS) -c Client_Dispatcher.c

flirChannels.o: flirChannels.c flirChannels.h
	gcc $(CCFLAGS) -c flirChannels.c

libusb_binary_protocol.o: libusb_binary_protocol.c
	gcc $(CCFLAGS) -c libusb_binary_protocol.c

Serializer_Struct.o: Serializer_Struct.c Serializer_Struct.h
	gcc $(CCFLAGS) -c Serializer_Struct.c

example: example.c $(SHARED_LIB)
	gcc $(CCFLAGS) example.c -o example $(SHARED_LIB) -lusb-1.0

install: libboson_sdk
	@echo "* Installing shared library to:" $(LIBRARY_DIR)$(SHARED_LIB)
	@sudo cp $(SHARED_LIB) $(LIBRARY_DIR)$(SHARED_LIB)
	@for file in $(HEADER_FILES); \
	do \
		echo "* Installing Boson header file:" $(INCLUDE_DIR)$$file; \
		sudo cp $$file $(INCLUDE_DIR)$$file; \
	done
	$(LDCONFIG)
clean:
	rm -f *~ *.o $(SHARED_LIB) example
