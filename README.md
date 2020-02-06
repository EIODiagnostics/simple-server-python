## Boson 320 simple webserver using resin.io

This is an adaptation of the resin.io "simple server with python flask" that builds a Docker image
with the Boson 320 SDK, Python bindings, udev rule, and Python camera to web server.

The building of the Docker image compiles the SDK, and copies files into the correct location for the target machine.

After making changes, push the code to the device:
```
$ git push resin master
```
It should take a few minutes for the code to push. While you wait, lets enable device URLs so we can see the server outside of our local network. This option can be toggled on the device summary page, pictured below or in the `Actions` tab in your device dashboards.

Then in your browser you should be able to open the device URL and see a simple webpage with a the output from the Boson 320.

[resin-link]:https://resin.io/
[signup-page]:https://dashboard.resin.io/signup
[gettingStarted-link]:http://docs.resin.io/#/pages/installing/gettingStarted.md
