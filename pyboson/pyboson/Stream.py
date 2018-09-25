
from enum import Enum
from ctypes import *

import numpy as np
import os.path
import time
import sys
import cv2

class BOSON_RESULT(Enum):
  BOSON_SUCCESS               = 0
  BOSON_ERROR_INVALID_DEVICE  = -1
  BOSON_ERROR_NO_CAPABILITY   = -2
  BOSON_ERROR_REQUEST_BUFFER  = -3
  BOSON_ERROR_QUERY_BUFFER    = -4
  BOSON_ERROR_VIDEO_MODE      = -5
  BOSON_ERROR_NOT_INITIALIZED = -6
  BOSON_ERROR_INVALID_PARAM   = -7
  BOSON_ERROR_MEMORY_ALLOC    = -8

# These constants and the code that relies on them will need to be revisited
# should we ever use a Flir camera that has a resolution other than 320x256.
VIDEO_WIDTH  = 320
VIDEO_HEIGHT = 256

boson_stream_lib = None;

def noop_callback(width, height, length, frame):
    return None

def display_callback(width, height, length, frame):
    # The dataframe being passed into us is (width * height) x 16 bit integers.
    # Read it in as a series of bytes.
    data_raw = bytes(string_at(frame, 2 * width * height))

    # We're going to be scaling the data frame down into an 8 bit gray scale
    # image, so allocate a Numpy array of (width * height) x 8 bit integers.
    data_8bit = np.zeros(((width * height), 1), dtype=np.uint8)

    # libboson_stream exports a basic linear Automatic Gain Control routine to
    # squash all the 16bit integers into an 8bit image.
    boson_stream_lib.boson_linear_agc(data_raw, c_void_p(data_8bit.ctypes.data), width, height);

    # Reshape the array from ((width * height), 1), to (height, width) so that
    # we can use it with OpenCV.
    data_8bit = np.reshape(data_8bit, (height, width));

    # Display the image.
    cv2.imshow("Boson Stream", data_8bit)
    cv2.waitKey(1)


class Stream(object):
    def __init__(self, device="/dev/video0", framerate=30):
        self.framerate = framerate

        # Keep a reference to the already loaded libboson_stream.so around.
        self._library = boson_stream_lib

        if os.path.exists(device):
            # Call the libboson_stream's initialize routine.  This will set up
            # Video4Linux to start streaming at our preferred resolution and
            # framerate.
            res = self._library.boson_stream_initialize(c_char_p(bytes(device, encoding="ascii")))
            if (BOSON_RESULT(res) != BOSON_RESULT.BOSON_SUCCESS):
                # We weren't able to initialize Video4Linux for use with the
                # Boson, so exit with an error message.
                sys.exit("Error: unable to initialize Boson: " + str(BOSON_RESULT(res)))
        else:
            # Unable to locate the specified device in /dev, so exit with an
            # error.
            sys.exit("Error: unable to locate Boson device at: " + device)

    def start(self, callback, pause=0.0):
        # Create a ctypes prototype for the callback function that we'll be
        # calling on every frame of video that comes back from the camera.
        # The callback function should accept four positional parameters:
        #
        #   width  - The width of the image in pixels
        #   height - The height of the image in pixels
        #   length - The length of the data frame
        #   frame  - The 16 bit raw data frame.
        prototype = CFUNCTYPE(None, c_int, c_int, c_int, POINTER(c_char_p))
        self.callback = prototype(callback)

        # Register the callback function with the underlying C library.
        res = self._library.boson_stream_start(c_float(pause), self.callback)

    def read(self):
      length = c_uint32()

      # Create a frame of (VIDEO_WIDTH * VIDEO_HEIGHT) 16-bit integers.
      frame = np.zeros(((VIDEO_WIDTH * VIDEO_HEIGHT), 1), dtype=np.uint16)

      # Get the current frame from the boson library.
      res = boson_stream_lib.boson_current_frame(c_void_p(frame.ctypes.data), byref(length))
      if BOSON_RESULT(res) != BOSON_RESULT.BOSON_SUCCESS:
        # If the call wasn't successful, return None instead of an image frame.
        return None

      # Reshape the frame into the size we'd expect.
      frame = np.reshape(frame, (VIDEO_HEIGHT, VIDEO_WIDTH))

      return frame

    def stop():
        self._library.boson_stream_stop()

    def __del__(self):
        self._library.boson_stream_shutdown()

if __name__ == '__main__':
    1
else:
    # Attempt to load the boson_stream shared library, which will give us access
    # to the Boson's image stream.  An OSError except will be raised if we're
    # not able to locate the library.
    dll_name = "libboson_stream.so"
    dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), dll_name))
    boson_stream_lib = cdll.LoadLibrary(dll_path)




