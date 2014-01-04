#!/usr/bin/python

import calendar
import re
import serial
import sys
import threading
import time

def degToDec(degree, direction):
    tmp_deg = (int)(degree / 100)
    tmp_min = (degree - (tmp_deg * 100)) / 60
    decimal = tmp_deg + tmp_min
    if (direction == 'N' or direction == 'E'):
        return decimal
    else:
        return -decimal

class GPGGA:
    def __init__(self, time=0, lat=0, NS=0, lon=0, EW=0, qual=0, numSat=0, HDOP=0, alt=0):
        self.time = hmsToList(time)
        self.lat = degToDec(lat, NS)
        self.lon = degToDec(lon, EW)
        self.qual = qual
        self.numSat = numSat
        self.HDOP = HDOP
        self.alt = alt
    
    def debug(self):
        print "\nGGA:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPGLL:
    def __init__(self, lat=0, NS='N', lon=0, EW='E', UTC=0, valid='V'):
        self.lat = degToDec(lat, NS)
        self.lon = degToDec(lon, EW)
        self.UTC = hmsToList(UTC)
        self.valid = valid
    
    def debug(self):
        print "\nGLL:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPGSA:
    def __init__(self, list=[]):
        self.mode1 = list[0]
        self.mode2 = list[1]
        self.satellites = filter(None, list[2:14])
        self.PDOP = list[-3]
        self.HDOP = list[-2]
        self.VDOP = list[-1]
    
    def debug(self):
        print "\nGSA:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPGSV:
    def __init__(self):
        self.tmp_sats = {}
    
    def storeSats(self, messages, msg_num, satsInView, *sats):
        if int(msg_num) == 1:
            self.tmp_sats = {}
        numSats = 4 if messages != msg_num else (satsInView - ((msg_num-1) * 4))
        for i in range(0, (numSats * 4), 4):
            SNR = sats[i+3] if sats[i+3] else None
            elv = sats[i+1] if sats[i+1] else None
            azi = sats[i+2] if sats[i+2] else None
            self.tmp_sats[sats[i]] = {'elevation': elv, 'azimuth': azi, 'SNR': SNR}
        if messages == msg_num:
            self.satellites = self.tmp_sats
    
    def debug(self):
        print "\nGSV:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPRMC:
    def __init__(self, UTC=0, valid='V', lat=0, NS=0, lon=0, EW=0, speed=0, course=0, date=0, variation=0, *trash):
        self.epoch = calendar.timegm(time.strptime(("%d %d" % (UTC, date)), "%H%M%S %d%m%y"))
        self.valid = True if valid == 'A' else False
        self.lat = degToDec(lat, NS)
        self.lon = degToDec(lon, EW)
        self.speed = speed if speed else None
        self.course = course if course else None
        self.variation = variation if variation else None
    
    def debug(self):
        print "\nRMC:"
        for property, value in vars(self).iteritems():
            print property + ":", value

class GPVTG:
    def __init__(self, course1=None, reference1='T',
                       course2=None, reference2=None,
                       speed1=None, units1=None,
                       speed2=None, units2=None):
        self.speed = {units1: speed1 if speed1 else None,
                      units2: speed2 if speed2 else None}
        self.course = {reference1: course1 if course1 else None,
                       reference2: course2 if course2 else None}
    
    def debug(self):
        print "\nVTG:"
        for property, value in vars(self).iteritems():
            print property + ":", value

#def updateSpeed(kmPerHr):
    # Convert to MPH
    
    # Set speed variable

def createCkSum(msg):
    ckSum = 0
    for c in msg:
        ckSum ^= ord(c)
    return(ckSum)

class myGPS(threading.Thread):
    def __init__(self, threadID, device):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = 'GPS-Thread'
        self.port = serial.Serial(device, baudrate=4800, timeout=2)
        self.port.close()
        self.port.open()
        self.running = False
        self.getMsg = None
        self.getCmd = None
        self.GSV = GPGSV()
    
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
                    if a[0] == 'GPGGA':
                        self.GGA = GPGGA(*a[1:10])
                        if self.getCmd == 'GGA':
                            self.getMsg = self.GGA
                            self.getCmd = None
                    elif a[0] == 'GPGSA':
                        self.GSA = GPGSA(a[1:])
                        if self.getCmd == 'GSA':
                            self.getMsg = self.GSA
                            self.getCmd = None
                    elif a[0] == 'GPGSV':
                        self.GSV.storeSats(*a[1:])
                        if self.getCmd == 'GSV':
                            self.getMsg = self.GSV
                            self.getCmd = None
                    elif a[0] == 'GPRMC':
                        self.RMC = GPRMC(*a[1:])
                        if self.getCmd == 'RMC':
                            self.getMsg = self.RMC
                            self.getCmd = None
                    elif a[0] == 'GPGLL':
                        self.GLL = GPGLL(*a[1:7])
                        if self.getCmd == 'GLL':
                            self.getMsg = self.GLL
                            self.getCmd = None
                    elif a[0] == 'GPVTG':
                        self.VTG = GPVTG(*a[1:9])
                        if self.getCmd == 'VTG':
                            self.getMsg = self.VTG
                            self.getCmd = None
                    else:
                        print "Unknown message type"
                else:
                    print 'Bad check-sum'
            else:
                print 'Incomplete message'
        print "Exiting " + self.name
    
    def stop(self):
        self.running = False
    
    def setRate(self, msg, rate):
        msgCode = {
            'GGA': 0, 'GLL': 1,
            'GSA': 2, 'GSV': 3,
            'RMC': 4, 'VTG': 5
            }
        self.__send_output('PSRF103,%02d,%02d,%02d,%02d' % (msgCode.get(msg, ''), 0, rate, 1))
    
    def getReport(self, msg):
        msgCode = {
            'GGA': 0, 'GLL': 1,
            'GSA': 2, 'GSV': 3,
            'RMC': 4, 'VTG': 5
            }
        timeout = 0
        maxTime = 3
        self.getCmd = msg
        self.__send_output('PSRF103,%02d,%02d,%02d,%02d' % (msgCode.get(msg, ''), 1, 0, 1))
        while timeout < maxTime and self.getMsg == None:
            time.sleep(0.05)
            timeout + 0.05
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

### Test Code ###
if __name__ == "__main__":
    reader = myGPS(1, sys.argv[1])
    reader.start()
    
    for i in range(1, 10):
        reader.getReport('VTG').debug()
    
    reader.running = 0
    print "Exiting main"
