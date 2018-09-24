#!/usr/bin/env python3

from pyboson.Stream import display_callback
from pyboson.Boson import Boson

import time

boson = Boson(callback=display_callback, device="/dev/video0")

boson.start(pause=0.0)

for i in range(20):
    frame = boson.read()
    print("Frame = " + str(frame))
    time.sleep(1)

time.sleep(30)

boson.stop()
