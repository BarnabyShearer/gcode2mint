#! /usr/bin/env python
import os
import select
import re
import time
import sys
import serial

feed_speed_multiplier = 3.5
feed_counts_multiplier = 317

def main():

    gcode = GCode(MintPrinter(sys.argv[1], 19200, timeout=.1))

    input, slave = os.openpty()
    print "Send G-Code to:", os.ttyname(slave)

    line = ''
    while True:
        select.select([input],[],[input])
        while True:
            c = os.read(input, 1)
            if c == '\x0A':
                break
            line += c

        line = line.lower()
        line = re.sub(r'\(.*\)', r'', line)
        line = re.sub(r';.*', r'', line)
        line = re.sub(r'^n[0-9-]+ ', r'', line)
        line = re.sub(r'\*[0-9]+', r'', line)

        line = line.replace('g', '|g')
        line = line.replace('m', '|m')
        print line

        for cmd in line.split('|'):
            if cmd!='':
                params = {}
                name = None
                value = ''
                for i in cmd:
                    if i == ' ':
                        continue
                    if i.isdigit() or i == '.' or i == '-':
                        value += i
                    else:
                        if name != None:
                            params[name] = float(value)
                        name = i
                        value = ''
                params[name] = float(value)
        
                if 'm' in params:
                    cmd = 'm%d' % params['m']
                    del params['m']
                elif 'g' in params:
                    cmd = 'g%d' % params['g']
                    del params['g']
                elif 't' in params:
                    cmd = 't%d' % params['t']
                    del params['t']
                else:
                    cmd = 'g1'
                code = getattr(gcode, cmd, None)
                if code != None:
                    os.write(input, 'ok %s\n' % (code(**params) or ''))
                else:
                    os.write(input, 'ok Not supported:%s\n' % cmd)
        line = ''
    
class GCode:

    metric = True
    absolute = True
    #Machine coords
    x = 0.0 #Assume at home
    y = 0.0
    z = 0.0
    #Working coords
    off_x = 0.0
    off_y = 0.0
    off_z = 0.0

    def __init__(self, printer):
        self.printer = printer

    def _units(self, v):
        if self.metric:
            return v
        else:
            return v * 0.0254

    def _ununits(self, v):
        if self.metric:
            return v
        else:
            return v/0.0254

    def m105(self):
        return 'T:0 /0 B:0 /0 @:0 B@:0'

    def g0(self, x=None, y=None, z=None, f=None, s=None, e=None):
        "Rapid move"
        self.g1(x, y, z, f, s)

    def g1(self, x=None, y=None, z=None, f=None, s=None, e=None):
        "Controlled move"
        if s!=None:
            self.printer.spindle(s)
        if f!=None:
            self.printer.feed(self._units(f))
        if x!=None:
            if self.absolute:
                self.x = self._units(x) + self.off_x
            else:
                 self.x += self._units(x)
        if y!=None:
            if self.absolute:
                self.y = self._units(y) + self.off_y
            else:
                 self.y += self._units(y)
        if z!=None:
            if self.absolute:
                self.z = self._units(z) + self.off_z
            else:
                 self.z += self._units(z)
        self.printer.move(
            self.x,
            self.y,
            self.z
        )
        pass

    def g4(self, p=None):
        """Dwell"""
        self.printer.wait()
        if not p > 0:
            p = 0
        time.sleep(p/1000)
    
    def g20(self):
        "Set Units to Inches"
        self.metric = False

    def g21(self):
        "Set Units to Millimeters"
        self.metric = True

    def g28(self, x=None, y=None, z=None):
        "Home"
        if x!= None:
            x = 0.0
        if y!= None:
            y = 0.0
        if z!= None:
            z = 0.0
        if x==None and y==None and z==None:
            x = 0.0
            y = 0.0
            z = 0.0
    
        self.g90() #Absolute
        self.g21() #Metric
        self.off_x = 0.0
        self.off_y = 0.0
        self.off_z = 0.0
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        #self.g0(x, y, z, f=2000) #Fast feed to home
        if z!=None:
            self.printer.home_z()
        if x!=None:
            self.printer.home_x()
        if y!=None:
            self.printer.home_y()

    def g40(self):
        "disable tool radius compensation"
        pass

    def g49(self):
        "disable tool length compensation"
        pass

    def g80(self):
        "cancel modal motion"
        pass

    def g54(self, x=None, y=None, z=None):
        "Work coordinate systems"
        if x != None or y != None or z != None:
            raise "Not implemented: G54 with values"

    def g61(self):
        "Exact path mode"
        pass

    def g80(self):
        "Cancel canned cycle"
        pass

    def g90(self):
        "Set to Absolute Positioning"
        self.absolute = True

    def g91(self):
        "Set to Relative Positioning"
        self.absolute = False

    def g92(self, x=None, y=None, z=None, e=None):
        "Set Position"
        if x != None:
            self.off_x = self.x - x
        if y != None:
            self.off_y = self.y - y
        if z != None:
            self.off_z = self.z - z
        if x == None and y == None and z == None:
            self.off_x = self.x
            self.off_y = self.y
            self.off_z = self.z

    def m0(self):
        "Stop"
        self.M18()

    def m1(self):
        "Optional Stop"
        pass

    def m2(self):
        "End of program"
        pass

    def m3(self, s=None):
        "Spindle on CW"
        self.printer.spindle_on()

    def m5(self):
        "Spindle off"
        self.printer.spindle_off()

    def m17(self):
        "Enable/Power all stepper motors"
        pass

    def m18(self):
        "Disable all stepper motors"
        self.M5()

    def m110(self, n=None):
        "Set Current Line Number"
        pass

    def m111(self, s=None):
        "Set Debug Level"
        pass
    
    def m112(self):
        "Emergency Stop"
        #TODO

    def m114(self):
        "Get Current Position"
        return "C: X:%f Y:%f Z:%f E:0.00" % (self._ununits(self.x), self._ununits(self.y), self._ununits(self.z))

    def m115(self):
        "Get Firmware Version and Capabilities"
        return "PROTOCOL_VERSION:0.1 FIRMWARE_NAME:gcode2mint MACHINE_TYPE:%s EXTRUDER_COUNT:0" % (
            self.printer.get_version()
	)
    
    def m116(self):
        "Wait"
        self.printer.wait()

    def t1(self):
        "Select Tool"
        #TODO        

def _checksum(buf):
    return chr(reduce(lambda x,y: x ^ y, [ord(l) for l in buf]))

class MintPrinter(serial.Serial):

    cmds = 0
    
    def _readall(self):
        buf = ''
        while True:
            b = self.read()
            if b == '':
                break
            buf += b
        msgs = ''
	print ">", buf
        for x in buf.split('\x02'):
            if '\x03' in x:
                msg = x[:x.find('\x03')+1]
                #assert _checksum(msg) == x[x.find('\x03'):]
                msgs += msg[:-1]
            else:
                msgs += x
        return msgs

    def _send_read(self, cmd, cmd_no=''):
	print cmd, cmd_no
        self.write("\x04%s%s\x05" % (cmd, cmd_no))
        return self._readall()

    def _send_enq(self, cmd, cmd_no=''):
        self.write("\x04%s%s\x05" % (cmd, cmd_no))

    def _send(self, cmd, cmd_no=''):
        buf = "\x04%s%s\x03" % (cmd, cmd_no)
        print cmd, cmd_no
        self.write(buf + _checksum(buf))

    def _wait(self):
	buf = self._send_read('ZZ6')
        try:
	    while buf[1] != 'z' or buf.split(",")[3] != '1' or buf.split(",")[4] != '1' or buf.split(",")[5] != '1':
                time.sleep(.1)
                buf = self._send_read('ZZ6')
        except:
            self._wait()

    def wait(self):
	self._wait();

    def get_version(self):
        return "%s.%s.%s" % (
            self._send_read('VN6'),
            self._send_read('MB6','31'),
            self._send_read('MB6','32')
        )

    def spindle(self, value):
        print "SET SPINDLE: %d" % value
        self._send('MB6', '(04,%04d' % value)

    def feed(self, value):
        print "SET FEED: %d" % value
        self._send('MB6', '(03,%04d' % (value*feed_speed_multiplier))

    def read_panel(self):
        return self._send_read('ZZ6')

    def home_x(self):
        print "HOMING: x"
        self._send_read('VN6')
        self._send_read('MB631')
        self._send_read('MB631')
        self._send_read('MB632')
        self._send_read('MB632')
        self._send('M312')
        self._send_read('MB67')
        self._send_read('MB67')
        self._send_read('VN6')
        self._send_read('MB619')
        self._send_read('MB65')
        self._send_read('MB66')
        self._send('MB6&20,60')
        self._send('MB6&01,20')
        self._send_enq('ZZ6')
        self._send('MB6(15,2800')
        self._send('CT6')
        self._send('MB6%08,0')
        self._send('MB6%09,0')
        self._send('MB6%10,0')
        self._send('MB6%34,0')
        self._send('MB6%38,0')
        self._send("MB6'04,150")
        self._send("MB6'06,100")
        self._send('MB6%02,0')
        
        self._send_read('ZZ6')
        self._send_read('ZZ6')
        self._send_read('ZZ6')
        self._send_read('ZZ6')

        self._send_enq('ZZ6')
        self._send('MB6%02,0')

        self._send_enq('ZZ6')
        self._send('HS6/2100,2100,2100')
        self._send_enq('ZZ6')
        self._send('HM0"2')
        self._wait()
        
    def home_y(self):
        print "HOMING: y"
        self._send_read('VN6')
        self._send_read('MB631')
        self._send_read('MB631')
        self._send_read('MB632')
        self._send_read('MB632')
        self._send('M312')
        self._send_read('MB67')
        self._send_read('MB67')
        self._send_read('VN6')
        self._send_read('MB619')
        self._send_read('MB65')
        self._send_read('MB66')
        self._send('MB6&20,60')
        self._send('MB6&01,20')
        self._send_enq('ZZ6')
        self._send('MB6(15,2800')
        self._send('CT6')
        self._send('MB6%08,0')
        self._send('MB6%09,0')
        self._send('MB6%10,0')
        self._send('MB6%34,0')
        self._send('MB6%38,0')
        self._send("MB6'04,150")
        self._send("MB6'06,100")
        self._send('MB6%02,0')
        
        self._send_read('ZZ6')
        self._send_read('ZZ6')
        self._send_read('ZZ6')
        self._send_read('ZZ6')

        self._send_enq('ZZ6')
        self._send('MB6%02,0')

        self._send_enq('ZZ6')
        self._send('HS6/2100,2100,2100')
        self._send_enq('ZZ6')
        self._send('HM1"2')
        self._wait()

    def home_z(self):
        print "HOMING: z"
        self._send_read('VN6')
        self._send_read('MB631')
        self._send_read('MB631')
        self._send_read('MB632')
        self._send_read('MB632')
        self._send('M312')
        self._send_read('MB67')
        self._send_read('MB67')
        self._send_read('VN6')
        self._send_read('MB619')
        self._send_read('MB65')
        self._send_read('MB66')
        self._send('MB6&20,60')
        self._send('MB6&01,20')
        self._send_enq('ZZ6')
        self._send('MB6(15,2800')
        self._send('CT6')
        self._send('MB6%08,0')
        self._send('MB6%09,0')
        self._send('MB6%10,0')
        self._send('MB6%34,0')
        self._send('MB6%38,0')
        self._send("MB6'04,150")
        self._send("MB6'06,100")
        self._send('MB6%02,0')
        
        self._send_read('ZZ6')
        self._send_read('ZZ6')
        self._send_read('ZZ6')
        self._send_read('ZZ6')

        self._send_enq('ZZ6')
        self._send('MB6%02,0')

        self._send_enq('ZZ6')
        self._send('MB6(03,2100')
        self._send('HS6/2100,2100,2100')

        self._send_enq('ZZ6')
        self._send('HM2"2')

        self._wait()

    def move(self, x, y, z):
        #TODO: ??? 3,4 
        print "MOVING TO: %d %d %d" % (x, y, z)
        self._send('VA6', '5-%05d,-%05d,-%05d' % (x*feed_counts_multiplier, y*feed_counts_multiplier, -z*feed_counts_multiplier))

    def spindle_on(self):
        print "SPINDLE ON"
	self._wait()
        self._send('MB6', '%18,3')
        self._send('MB6', '&01,18')
	self._wait()

    def spindle_off(self):
        print "SPINDLE OFF"
	self._wait()
        self._send('MB6', '%18,5')
        self._send('MB6', '&01,18')
	self._wait()

if __name__ == "__main__":
    main()
