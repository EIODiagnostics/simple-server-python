#!/usr/bin/env python3

from pyboson.Stream import display_callback
from pyboson.Boson import Boson

import time

boson = Boson(device="/dev/video0")

boson.stream.start(display_callback, pause=0.1)

time.sleep(30)
