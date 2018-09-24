HEADER_FILES = boson_stream.h
SHARED_LIB   = libboson_stream.so

INCLUDE_DIR  = /usr/local/include/
LIBRARY_DIR  = /usr/local/lib/

CCFLAGS = -fPIC -O4 -g

LDCONFIG     = @/sbin/ldconfig

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
        SHARED_LIB = libboson_stream.dylib
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
all: libboson_stream

libboson_stream: boson_stream.o
	gcc $(CCFLAGS) -shared -o $(SHARED_LIB) boson_stream.o -lpthread

boson_stream.o: boson_stream.c boson_stream.h
	gcc $(CCFLAGS) -c boson_stream.c -lpthread

install: libboson_stream
	@echo "* Installing shared library to:" $(LIBRARY_DIR)$(SHARED_LIB)
	@cp $(SHARED_LIB) $(LIBRARY_DIR)$(SHARED_LIB)
	@for file in $(HEADER_FILES); \
	do \
		echo "* Installing Boson stream header file:" $(INCLUDE_DIR)$$file; \
		cp $$file $(INCLUDE_DIR)$$file; \
	done
	@/sbin/ldconfig

clean:
	rm -f *~ *.o $(SHARED_LIB)
