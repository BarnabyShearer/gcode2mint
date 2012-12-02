gcode2mint.py
=============

Allows driving the Denford MicroMill 2000 (and hopfully similar devices) via standard g-code.

This is still very early days, but alread implements enough for most CAM output.

Usage
-----

::

    mint2gcode.py /dev/ttyS0

The example assumes the Denford is connected to your first serial port. This will then print a /dev/pts/ you can
send the g-code to. Any host software should work, but I have been using [https://github.com/kliment/Printrun.git].

The g-code is loosly based on the RepRap style, and dosn't implement any tool or work offsets. Ensure your CAM
sysytem pre-calculates them. It is tested with [http://pycam.sourceforge.net/].

Protocol
--------

The MINT protocol implemented is documented here [http://readinghackspace.org.uk/wiki/CNCMill_Mint].

Source
------

You can get the latest version via:

::

    git clone https://Zi.iS/c/gcode2mint
