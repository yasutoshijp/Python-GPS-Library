#!/usr/bin/python

import calendar
import re
import serial
import sys
import threading
import time

class GPGGA:
    def __init__(self, msg_list):
        self.time = hmsToList(msg_list[0])
        self.lat = degToDec(msg_list[1], msg_list[2])
        self.lon = degToDec(msg_list[3], msg_list[4])
        self.qual = msg_list[5]
        self.numSat = msg_list[6]
        self.HDOP = msg_list[7]
        self.alt = msg_list[8]
    
    def debug(self):
        print "\nGGA:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPGLL:
    def __init__(self, msg_list):
        self.lat = degToDec(msg_list[0], msg_list[1])
        self.lon = degToDec(msg_list[2], msg_list[3])
        self.UTC = hmsToList(msg_list[4])
        self.valid = msg_list[5]
    
    def debug(self):
        print "\nGLL:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPGSA:
    def __init__(self, msg_list):
        self.mode1 = msg_list[0]
        self.mode2 = msg_list[1]
        self.satellites = filter(None, msg_list[2:14])
        self.PDOP = msg_list[-3]
        self.HDOP = msg_list[-2]
        self.VDOP = msg_list[-1]
    
    def debug(self):
        print "\nGSA:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPGSV:
    def __init__(self):
        self.tmp_sats = {}
        self.satellites = {}
    
    def storeSats(self, msg_list):
        messages = msg_list[0]
        msg_num = msg_list[1]
        satsInView = msg_list[2]
        sats = msg_list[3:]
        
        # Reset satellites if first message
        if int(msg_num) == 1:
            self.tmp_sats = {}
        
        # How many satellites in message
        numSats = 4 if messages != msg_num else (satsInView - ((msg_num-1) * 4))
        
        # Set to dictionary
        for i in range(0, (numSats * 4), 4):
            SNR = sats[i+3] if sats[i+3] else None
            elv = sats[i+1] if sats[i+1] else None
            azi = sats[i+2] if sats[i+2] else None
            self.tmp_sats[sats[i]] = {'elevation': elv, 'azimuth': azi, 'SNR': SNR}
        
        # If last message save tmp to data
        if messages == msg_num:
            self.satellites = self.tmp_sats
            self.debug()
    
    def debug(self):
        print "\nGSV:"
        print self.satellites

class GPRMC:
    def __init__(self, msg_list):
        self.epoch = calendar.timegm(time.strptime(("%d %d" % (msg_list[0], msg_list[8])), "%H%M%S %d%m%y"))
        self.valid = True if msg_list[1] == 'A' else False
        self.lat = degToDec(msg_list[2], msg_list[3])
        self.lon = degToDec(msg_list[4], msg_list[5])
        self.speed = msg_list[6] if msg_list[6] else None
        self.course = msg_list[7] if msg_list[7] else None
        self.variation = msg_list[9] if msg_list[9] else None
    
    def debug(self):
        print "\nRMC:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPVTG:
    def __init__(self, msg_list):
        self.speed = {msg_list[5]: msg_list[4] if msg_list[4] else None,
                      msg_list[7]: msg_list[6] if msg_list[6] else None}
        self.course = {msg_list[1]: msg_list[0] if msg_list[0] else None,
                       msg_list[3]: msg_list[2] if msg_list[2] else None}
    
    def debug(self):
        print "\nVTG:"
        for property, value in vars(self).iteritems():
            print property + ":", value

def createCkSum(msg):
    ckSum = 0
    for c in msg:
        ckSum ^= ord(c)
    return(ckSum)

class GPS(threading.Thread):
    def __init__(self, threadID, device):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = 'GPS-Thread'
        self.port = serial.Serial(device, baudrate=4800, timeout=2)
        self.port.close()
        self.port.open()
        self.running = False
        self.msgCodes = {
            'GPGGA': 0, 'GPGLL': 1, 'GPGSA': 2, 'GPGSV': 3, 'GPRMC': 4, 'GPVTG': 5
        }
        self.getMsg = None
        self.getCmd = None
        self.objects = {
            'GPGGA': {'data': None, 'handler': None, 'factory': GPGGA},
            'GPGLL': {'data': None, 'handler': None, 'factory': GPGLL},
            'GPGSA': {'data': None, 'handler': None, 'factory': GPGSA},
            'GPGSV': {'data': GPGSV(), 'handler': None, 'factory': None},
            'GPRMC': {'data': None, 'handler': None, 'factory': GPRMC},
            'GPVTG': {'data': None, 'handler': None, 'factory': GPVTG}
        }
        self.objects['GPGSV']['factory'] = self.objects['GPGSV']['data'].storeSats
    
    def run(self):
        self.running = True
        nmea = re.compile('^\$([^*]+)\*(..)')
        while(self.running):
            msg = self.port.readline()
            msg = msg.replace('\x00', '')
            x = nmea.match(msg)
            if x:
                self.ckSum = int(x.group(2), 16)
                self.msg = x.group(1)
                self.isGood = False if createCkSum(self.msg) != self.ckSum else True
                if self.isGood:
                    a = self.msg.rsplit(',')
                    listToTypes(a)
                    
                    # Store data
                    if a[0] != 'GPGSV':
                        self.objects[a[0]]['data'] = self.objects[a[0]]['factory'](a[1:])
                    
                    # Pass to any handler
                    if self.objects[a[0]]['handler']:
                        self.objects[a[0]]['handler'](self.objects[a[0]]['data'])
                    
                    # Place data for getting report
                    if self.getCmd == a[0]:
                        if a[0] == 'GPGSV' and a[1] != a[2]:
                            continue
                        self.getMsg = self.objects[a[0]]['data']
                        self.getCmd = None
                else:
                    print 'Bad check-sum'
            else:
                print 'Incomplete message'
                self.port.flushInput()
        print "Exiting " + self.name
    
    def stop(self):
        self.running = False
    
    def setRate(self, msg, rate):
        self.__send_output('PSRF103,%02d,%02d,%02d,%02d' % (self.msgCodes.get(msg, ''), 0, rate, 1))
    
    def getReport(self, msg):
        # Form message
        self.getCmd = msg
        print 'Message requested'
        self.__send_output('PSRF103,%02d,%02d,%02d,%02d' % (self.msgCodes.get(msg, 99), 1, 0, 1))
        
        # Wait for message
        timeout = 0
        maxTime = 1
        while timeout < maxTime and self.getMsg == None:
            time.sleep(0.1)
            timeout += 0.1
        
        # Save message, reset, and return
        newMsg = self.getMsg
        self.getMsg = None
        return newMsg
    
    def __send_output (self, msg):
        self.port.write('$'+msg+'*%02x\r\n' % (createCkSum(msg)))

def listToTypes(l):
    for idx in range(0, len(l)):
        try:
            tmp_flt = float(l[idx])
            tmp_int = int(tmp_flt)
            l[idx] = tmp_int if tmp_int == tmp_flt else tmp_flt
        except:
            None

def hmsToList(hms):
    hour = (int)(hms / 10000)
    remainder = hms % 10000
    minutes = (int)(remainder / 100)
    seconds = remainder % 100
    return(hour, minutes, seconds)

def degToDec(degree, direction):
    try:
        tmp_deg = (int)(degree / 100)
        tmp_min = (degree - (tmp_deg * 100)) / 60
        decimal = tmp_deg + tmp_min 
    except:
        print "Degree:", degree
        decimal = 0
    
    if (direction == 'N' or direction == 'E'):
        return decimal
    else:
        return -decimal

def printObject(obj):
    obj.debug()

### Test Code ###
if __name__ == "__main__":
    reader = GPS(1, sys.argv[1])
    reader.start()
    #reader.objects['GPGGA']['handler'] = printObject
    
    str = None
    while str != "quit" and reader.isAlive():
        str = raw_input(" $ ")
        match = re.match("^(GET|RATE) (.*)", str.upper())
        if match:
            if match.group(1) == 'GET':
                msg = reader.getReport(match.group(2))
                if msg:
                    msg.debug()
            elif match.group(1) == 'RATE':
                print match.group(2)
                reader.setRate(match.group(2).rsplit(' '))
        elif reader.objects.get(str, None):
            print(reader.objects[str]['data'].debug())
        elif str != '' and str != 'quit':
            print "Object has no "+str
    
    reader.running = 0
    print "Exiting main"