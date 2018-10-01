#!/usr/bin/env python3

from datetime import datetime
from ctypes import *

import numpy as np
import threading
import logging
import time
import yaml
import cv2
import os
from datetime import datetime
from ctypes import *
from signal import signal, SIGABRT, SIGILL, SIGINT, SIGSEGV, SIGTERM
import sys
from twisted import web
from twisted.web.static import File as WebFile
from twisted.web.resource import Resource
from twisted.internet import reactor, endpoints
from twisted.internet.task import deferLater
from twisted.web.resource import NoResource
from twisted.python import log
from pyboson.Stream import display_callback
from pyboson.Boson import Boson

# https://stackoverflow.com/a/4060259/54745
__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

libboson_stream = cdll.LoadLibrary(os.path.join(__location__, "pyboson", "libboson_stream.so"))

class Settings:
    def __init__(self):
        self.fpm_start = None
        self.fpm_count = 0
        self.last_frame_sent = 0
        self.frame_count = 0
        self.bufferLength = 1
        self.bufferIndex = 0
        # TODO: replace this with preallocation of correct image frame size
        # however these None's are used by the DelayedResource handler for serving images
        self.rawBuffer = [None] * self.bufferLength
        self.pngBuffer = [None] * self.bufferLength
        self.bufferLock = threading.RLock()
        self.boson_preview = 0
        self.boson_save_images_locally = 0
        self.boson_path = ""

settings = Settings()

class DelayedResource(Resource):
    global settings
    isLeaf = True

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def _delayedPng(self, request):
        try:  
            with settings.bufferLock:
                image = settings.pngBuffer[settings.bufferIndex]
                settings.pngBuffer[settings.bufferIndex] = None
                frame_count = settings.frame_count
                settings.last_frame_sent = frame_count
            if image is None:
                self.logger.debug("no PNG frame to send")
                request.setResponseCode(404)
                request.write(b"no PNG frame to send")
                request.finish()
                return
            else:
                self.logger.debug("sending PNG frame " + str(frame_count))
                request.setHeader(b'Content-type', b'image/png')
                request.setHeader(b'Content-Length', str(len(image)).encode('utf-8'))
                request.setHeader(b'Frame-count', str(frame_count).encode('utf-8'))
                request.write(image.tobytes())
                request.setResponseCode(200)
                request.finish()
                return
        except BaseException as e:
            traceback.print_exc(file=sys.stdout)
            raise e

    def _delayedRaw(self, request):
        try:  
            with settings.bufferLock:
                image = settings.rawBuffer[settings.bufferIndex]
                settings.rawBuffer[settings.bufferIndex] = None
                frame_count = settings.frame_count
                settings.last_frame_sent = frame_count
            if image is None:
                self.logger.debug("no RAW frame to send")
                request.setResponseCode(404)
                request.write(b"no RAW frame to send")
                request.finish()
                return
            else:
                self.logger.debug("sending RAW frame " + str(frame_count))
                request.setHeader(b'Content-type', b'application/octet-stream')
                request.setHeader(b'Content-Length', str(len(image)).encode('utf-8'))
                request.setHeader(b'Frame-count', str(frame_count).encode('utf-8'))
                request.write(image)
                request.setResponseCode(200)
                request.finish()
                return
        except BaseException as e:
            traceback.print_exc(file=sys.stdout)
            raise e

    def render_GET(self, request):
        self.logger.debug("render_GET request " + str(request.postpath))
        d = deferLater(reactor, 0, lambda: request)

        if b"latest.png" in request.postpath:
            d.addCallback(self._delayedPng)
            return web.server.NOT_DONE_YET

        elif b"latest.raw" in request.postpath:
            d.addCallback(self._delayedRaw)
            return web.server.NOT_DONE_YET

        else:
            self.logger.debug("request not supported")
            request.setHeader(b'Content-Length', 0)
            request.setResponseCode(400)
            return (b"<!DOCTYPE html><html><head><meta charset='utf-8'>"
                    b"<title></title></head><body>request not supported</body></html>")


class BosonMonitorThread(threading.Thread):
    def __init__(self, fpm_threshold = 0):
        threading.Thread.__init__(self)

        self.fpm_threshold = fpm_threshold
        self.logger        = logging.getLogger(__name__)
        self.name          = "monitor"
        self.stop          = False

    def run(self):
        self.logger.info("Starting Boson monitor thread with a FPM threshold of: " + str(self.fpm_threshold))

        global settings
        settings.fpm_start = datetime.now()
        settings.fpm_count = 0

        while not self.stop:
            now = datetime.now()

            # Keep track of our frames per minute info.
            # Boson camera.
            if ((now - settings.fpm_start).seconds >= 60):
                with settings.bufferLock:
                   fpm_count = settings.fpm_count
                   settings.fpm_count = 0

                self.logger.info("Boson frames per minute: " + str(fpm_count))
                settings.fpm_start = now

            time.sleep(1)

    def shutdown(self):
        self.stop = True

def BosonCallback(width, height, length, frame):
    logger = logging.getLogger(__name__)

    global libboson_stream
    global settings
    with settings.bufferLock:
        settings.fpm_count += 1
        if settings.frame_count > (settings.bufferLength + settings.last_frame_sent):
            logger.debug("dropping frame")
            return
    
    # The dataframe being passed into us is (width * height) * 16 bit integers.
    # Read it in as a series of bytes.
    image_raw = bytes(string_at(frame, 2 * width * height))

    # now the 8 bit data
    data_8bit = np.zeros(((width * height), 1), dtype=np.uint8)

    libboson_stream.boson_linear_agc(image_raw, c_void_p(data_8bit.ctypes.data), width, height);

    data_8bit = np.reshape(data_8bit, (height, width));
    (retval, image_8bit) = cv2.imencode(".png", data_8bit)

    # save image into memory buffer
    with settings.bufferLock:
        settings.frame_count += 1
        logger.debug("frame " + str(settings.frame_count))
        settings.bufferIndex = settings.frame_count % settings.bufferLength
        settings.rawBuffer[settings.bufferIndex] = image_raw
        settings.pngBuffer[settings.bufferIndex] = image_8bit

    if settings.boson_save_images_locally:
        timestamp = datetime.now()
        epoch_timestamp = str(int(round(time.time() * 1000)))

        # We'll be archiving images in subdirectories, otherwise the
        # sheer number of images overwhelms most of the comand line
            # tools like "cp" and "rm".
        image_dir = "{}".format(timestamp.strftime("%Y_%m_%d_%H"))
        os.makedirs(settings.boson_path + "/" + image_dir, exist_ok = True)

        # Create the path that we'll be saving our raw image data to.
        image_path = settings.boson_path + "/" + image_dir + "/" + epoch_timestamp + ".raw"
        logger.debug("Saving raw Boson image data to: " + image_path)

        file = open(image_path, "wb")
        file.write(image_raw)
        file.close()

    if settings.boson_preview:
        image_8bit_path = settings.boson_path + "/" + "latest.png"
        logger.debug("Saving image preview to: " + image_8bit_path);
        file = open(image_8bit_path, "wb")
        file.write(image_8bit)
        file.close()

class BosonThread (threading.Thread):
    def __init__(self, path="", pause=0.0, device="/dev/device0", flip_vertical=True):
        threading.Thread.__init__(self)

        self.flip_vertical = flip_vertical
        self.logger        = logging.getLogger(__name__)
        self.name          = "boson"
        self.path          = path
        self.pause         = pause
        self.device        = device
        self.stop          = False

    def run(self):
        self.logger.debug("Starting Boson capture thread.")

        boson = Boson(device=self.device)

        boson.stream.start(BosonCallback, pause=self.pause)

        while 1:
            time.sleep(1)
        self.logger.info("Exiting Boson capture thread.")

    def shutdown(self):
        self.stop = True


class DataCapture():
    def __init__(self, config = ""):
        global settings
        self.logger = logging.getLogger(__name__)

        # initial logging before the configuration is loaded
        logging.basicConfig(format   = '[%(asctime)s] [%(threadName)s] [%(levelname)s] %(message)s',
                            datefmt  = '%m/%d/%Y %I:%M:%S %p',
                            level    = logging.DEBUG)
        
        self.http_root           = None
        self.http_port           = 8080
        self.http_enable         = 1
        self.log_level           = 0
        self.log_file            = None
        self.boson_enable        = 1
        self.boson_pause         = 10
        self.boson_dev           = ""
        self.boson_fpm_threshold = 0

        threading.current_thread().name = "main"

        if config != "":
            self.load_config(config)

        # reconfigure logging based on loaded configuration
        logging.basicConfig(format   = '[%(asctime)s] [%(threadName)s] [%(levelname)s] %(message)s',
                            datefmt  = '%m/%d/%Y %I:%M:%S %p',
                            filename = self.log_file,
                            level    = logging.DEBUG)
        


    def load_config(self, config_file):
        # Load the configuration file, if it exists.
        try:
            self.logger.info("Reading configuration from file: {}".format(config_file));
            with open(config_file, 'r') as stream:
                config = yaml.load(stream)

                for key, val in config.items():
                    # http-root specifies the directory that our HTTP server will
                    # be serving images out of.
                    if key == "http-root":
                        self.http_root = os.path.join(__location__, config["http-root"])
                        self.logger.debug("Setting http_root to: " + self.http_root)

                    # http-port sets the port for the http server to listen on
                    elif key == "http-port":
                        self.http_port = int(config["http-port"])
                        self.logger.debug("Setting http_port to: " + str(self.http_port))

                    # http-enable enables the HTTP server used to access and monitor
                    # the program while running.
                    elif key == "http-enable":
                        self.http_enable = config["http-enable"]
                        self.logger.debug("Setting HTTP server enable to: " + str(self.http_enable))

                    # log-level controls the verbosity of our logging.  Set to
                    # one of debug, info, warning, error, or critical.
                    elif key == "log-level":
                        self.log_level = config["log-level"]
                        self.logger.debug("Setting log_level to: " + self.log_level)
                        if self.log_level == "debug":
                            self.logger.setLevel(logging.DEBUG)
                        elif self.log_level == "info":
                            self.logger.setLevel(logging.INFO)
                        elif self.log_level == "warning":
                            self.logger.setLevel(logging.WARNING)
                        elif self.log_level == "error":
                            self.logger.setLevel(logging.ERROR)
                        elif self.log_level == "critical":
                            self.logger.setLevel(logging.CRITICAL)

                    # If log-file is set, redirect all the logging to the specified file.  If left
                    # unset, logs will be printed to STDERR.
                    elif key == "log-file":
                        self.log_file = os.path.join(__location__, config["log-file"])
                        self.logger.debug("Setting log file to: " + self.log_file)

                    # boson-preview outputs PNG images of the raw data.
                    elif key == "boson-preview":
                        settings.boson_preview = bool(config["boson-preview"])
                        self.logger.debug("Setting boson_preview to: " + str(settings.boson_preview))

                    # boson-enable enables the Boson when set to 1, and disables
                    # it when set to 0.
                    elif key == "boson-enable":
                        self.boson_enable = int(config["boson-enable"])
                        self.logger.debug("Setting boson_enable to: " + str(self.boson_enable))

                    # boson-fpm-threshold is the value at which any frame rate that
                    # falls below the threshold will trigger a boson reboot.
                    elif key == "boson-fpm-threshold":
                        self.boson_fpm_threshold = int(config["boson-fpm-threshold"])
                        self.logger.debug("Setting boson_fpm_threshold to: " + str(self.boson_fpm_threshold))

                    # boson-pause specifies the number of seconds to wait before
                    # obtaining another image from the Boson.
                    elif key == "boson-pause":
                        self.boson_pause = float(config["boson-pause"])
                        self.logger.debug("Setting boson_pause to: " + str(self.boson_pause))

                    # boson-save-images-locally specifies if images should be saved locally.
                    # saves png and raw images when set to 1, does not save if set to 0.
                    elif key == "boson-save-images-locally":
                        settings.boson_save_images_locally = int(config["boson-save-images-locally"])
                        self.logger.debug("Setting boson-save-images-locally to: " + str(settings.boson_save_images_locally))

                    # boson-save-path specifies the directory used to save the
                    # images obtained from the Boson.
                    elif key == "boson-save-path":
                        settings.boson_path = os.path.join(__location__, config["boson-save-path"])
                        self.logger.debug("Setting boson_path to: " + str(settings.boson_path))

                    # boson-device specifies the path we expect to find a Boson camera
                    # at.  This is almost always /dev/video0, though occasionally, the
                    # camera will appear at /dev/video1.
                    elif key == "boson-device":
                        self.boson_dev = config["boson-device"]
                        self.logger.debug("Setting boson_dev to: " + str(self.boson_dev))

                    else:
                        self.logger.info("Unknown key in configuration file: " + key)
        except Exception as e:
            self.logger.error("Unable to load configuration file: {}".format(e))
            return

    def start(self):
        global seettings
        # Initialize and start the HTTP server thread if it has been enabled.
        if self.http_enable:
            self.logger.info("Starting the HTTP server thread...")

            root = WebFile(self.http_root)
            root.putChild(b"boson", DelayedResource())
            self.http_factory = web.server.Site(root)
            self.http_endpoint = endpoints.TCP4ServerEndpoint(reactor, self.http_port)
            self.http_endpoint.listen(self.http_factory)
            log.msg("running reactor")
            self.http_reactorThread = threading.Thread(target=reactor.run, args=(False,))
            self.http_reactorThread.start()
        else:
            self.logger.warning("HTTP server thread is disabled.")
            self.resource = None

        # Initialize and start the Boson camera capture thread if it has been
        # enabled.
        if self.boson_enable:
            self.logger.info("Starting Boson capture thread...")
            self.boson_thread = BosonThread(path   = settings.boson_path,
                                            pause  = self.boson_pause,
                                            device = self.boson_dev)
            self.boson_thread.start()

            # Start the monitor thread that keeps an eye on the Boson and
            # reboots it if necessary.
            self.boson_monitor = BosonMonitorThread(fpm_threshold = self.boson_fpm_threshold)
            self.boson_monitor.start()
        else:
            self.logger.warning("Boson capture thread is disabled.")

        # Wait until we get a keyboard interupt to shutdown.
        try:
            while 1:
                time.sleep(.1)
        except KeyboardInterrupt:
            self.logger.info("Shutting down, please wait...")
            print("Shutting down, please wait...")
            self.shutdown()

        os._exit(0)

        # Wait for the child threads to exit.
        if self.http_enable:
            self.http_thread.join()
        if self.boson_enable:
            self.boson_thread.join()
            self.boson_monitor.join()

    def shutdown(self):
        if self.http_enable:
            self.logger.info("Shutting down the HTTP server thread...")
            reactor.stop()
            #self.http_thread.shutdown()

        if self.boson_enable:
            self.logger.info("Shutting down the Boson capture thread...")
            self.boson_thread.shutdown()
            self.boson_monitor.shutdown()

def main():
    #config_file = "/home/cspencer/git/boson-capture/config.yaml"
    config_file = os.path.join(__location__, "config.yaml")
    capture = DataCapture(config = config_file)

    capture.start()

if __name__ == "__main__":
    if False:
      from old_boson_capture import old_main
      old_main()
    else:
      main()
