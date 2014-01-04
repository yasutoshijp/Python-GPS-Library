import Adafruit_BBIO.UART as UART
from time import sleep
import serial

CONSTANTS = {
    # Commands
    'CLEARDISPLAY': 0x01,
    'CURSORSHIFT': 0x10, 'CURSORLEFT': 0x18, 'CURSORRIGHT': 0x1C,
    'ENTRYMODESET': 0x04,
    'FUNCTIONSET': 0x20,
    'SETCGRAMADDR': 0x40, 'SETDDRAMADDR': 0x80,
    'SETSPLASHSCREEN': 0x0A, 'SPLASHTOGGLE': 0x09,
    'RETURNHOME': 0x02,

    # Display Entry Mode
    'ENTRYRIGHT': 0x00,
    'ENTRYLEFT': 0x02,

    # Flags for display on/off control
    'DISPLAYCONTROL': 0x08,
    'BLINKON': 0x01,
    'CURSORON': 0x02,
    'DISPLAYON': 0x04,
    'BACKLIGHT': 0x80,

    #  Flags for setting display
    'BAUD': 9600,
    'SET2LINE': 0x06,
    'SET4LINE': 0x05,
    'SET16CHAR': 0x04,
    'SET20CHAR': 0x03,
    '2LINE': 0x02,
    '4LINE': 0x04,
    '16CHAR': 0x10,
    '20CHAR': 0x14,

    # LCD Types
    '2X16': 3,
    '2X20': 4,
    '4X16': 5,
    '4X20': 6,
}

# Broken #
def cursor():
    global __display_control
    __display_control = __display_control | CONSTANTS['CURSORON']
    __command(CONSTANTS['DISPLAYCONTROL'] | __display_control)

def no_cursor():
    global __display_control
    __display_control = __display_control & (~CONSTANTS['CURSORON'] & 0xFF)
    __command(CONSTANTS['DISPLAYCONTROL'] | __display_control)

def display():
    global __display_control
    __display_control = __display_control | CONSTANTS['DISPLAYON']
    __command(CONSTANTS['DISPLAYCONTROL'] | __display_control)

def no_display():
    global __display_control
    __display_control = __display_control & (~CONSTANTS['DISPLAYON'] & 0xFF)
    __command(CONSTANTS['DISPLAYCONTROL'] | __display_control)

def create_char(location, charmap):
    location -= 1
    location = location & 0x07
    for i in range(0, 8):
        __command(CONSTANTS['SETCGRAMADDR'] | (location << 3) | i)
        serial.write(charmap[i])

def print_custom_char(num):
    serial.write(num - 1)

def left_to_right():
    global __display_mode
    __display_mode = __display_mode | CONSTANTS['ENTRYLEFT']
    __command(CONSTANTS['ENTRYMODESET'] | __display_mode)

def right_to_left():
    global __display_mode
    __display_mode = __display_mode & (~CONSTANTS['ENTRYLEFT'] & 0xFF)
    __command(CONSTANTS['ENTRYMODESET'] | __display_mode)

def blink():
    global __display_control
    __display_control = __display_control | CONSTANTS['BLINKON']
    __command(CONSTANTS['DISPLAYCONTROL'] | __display_control)

def no_blink():
    global __display_control
    __display_control = __display_control & (~CONSTANTS['BLINKON'] & 0xFF)
    __command(CONSTANTS['DISPLAYCONTROL'] | __display_control)

def set_type(lcd_type):
    # 3: type 2x16
    # 4: type 2x20
    # 5: type 4x16
    # 6: type 4x20
    __special_command(lcd_type)
    if(lcd_type == 3):
        __num_lines = CONSTANTS['2LINE']
        __num_chars = CONSTANTS['16CHAR']
    elif lcd_type == 4:
        __num_lines = CONSTANTS['2LINE']
        __num_chars = CONSTANTS['20CHAR']
    elif lcd_type == 5:
        __num_lines = CONSTANTS['4LINE']
        __num_chars = CONSTANTS['16CHAR']
    elif lcd_type == 6:
        __num_lines = CONSTANTS['4LINE']
        __num_chars = CONSTANTS['20CHAR']
    else:
        __num_lines = CONSTANTS['2LINE']
        __num_chars = CONSTANTS['16CHAR']
# End Broken #

class serLCD():
    def __init__(self, port):
        self.__display_control = 0
        self.__num_lines = 2
        self.__num_rows = 20
        self.port = serial.Serial(port=port, baudrate=9600)
        self.port.close()
        self.port.open()
        self.clear()
    
    def clear(self):
        self.__command(CONSTANTS['CLEARDISPLAY'])
    
    def clear_line(self, line):
        if(line > 0 and line <= self.__num_lines):
            set_cursor(line, 1)
            self.port.write(" " * self.__num_rows)
            set_cursor(line, 1)
    
    def home(self):
        self.__command(CONSTANTS['RETURNHOME'])
    
    def write(self, msg):
        self.port.write(msg)
    
    def scroll_left(self):
        self.__command(CONSTANTS['SCROLLLEFT'])
    
    def scroll_right(self):
        self.__command(CONSTANTS['SCROLLRIGHT'])
    
    def select_line(self, line):
        if(line > 0 and line <= self.__num_lines):
            self.set_cursor(line, 1)
    
    def set_brightness(self, num):
        if(num >= 1 and num <= 30):
            self.__special_command(CONSTANTS['BACKLIGHT'] | (num - 1))
    
    def set_cursor(self, row, col):
        _rowoffset = 0
        row_offsets = [
            [ 0x00, 0x40, 0x10, 0x50 ],
            [ 0x00, 0x40, 0x14, 0x54 ]
        ]
        if((row > 0 and row < 3) and (col > 0 and col < 17)):
            self.__command(CONSTANTS['SETDDRAMADDR'] | ((col - 1) + row_offsets[_rowoffset][row - 1]))
    
    def set_splash(self):
        self.__special_command(CONSTANTS['SETSPLASHSCREEN'])
    
    def toggle_splash(self):
        self.__special_command(CONSTANTS['SPLASHTOGGLE'])
    
    def __command(self, value):
        self.port.write(chr(0xfe))
        self.port.write(chr(value))
        sleep(0.005)

    def __special_command(self, value):
        self.port.write(chr(0x7C))
        self.port.write(chr(value))
        sleep(0.005)

if __name__ == "__main__":
    UART.setup("UART1")
    serial = serial.Serial(port = "/dev/ttyO1", baudrate=9600)
    serial.close()
    serial.open()
    if serial.isOpen():
        print "Using UART1"
        clear()
        serial.write("Hello")
        select_line(2)
        serial.close()

