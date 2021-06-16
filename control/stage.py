import serial
from serial.tools import list_ports
import time
import numpy as np
from timeit import default_timer as timer
from abc import ABC, abstractmethod

class Stage(ABC):

    @abstractmethod
    def get_position(self):
        pass

    @abstractmethod
    def move_relative(self,x,y):
        pass

    @abstractmethod
    def move_absolute(self,x,y):
        pass


class TangoStage(Stage):

    def __init__(self):
        self.ser = self.find_port()
        self.write('!autostatus 1')
        self.pos = self.get_position()
        print(f'stage initial position: {self.pos}')

    def find_port(self):
        for port in list_ports.comports():
            try:
                ser = serial.Serial(port.device, 57600, timeout=0.2)
                ser.write(b'?version \r')
                r = ser.readline()
                if b'TANGO' in r:
                    print(f'stage found on port {port}')
                    return ser
            except Exception as e:
                print(e)
                print(f'did not connect stage on port {port}')

    def write(self, write):
        self.ser.write(str.encode(write + ' \r'))

    def read(self):
        return self.ser.readline().decode().strip()

    def get_position(self):
        self.write('?pos')
        pos = self.read()
        self.pos = [float(pos.split(' ')[0]),float(pos.split(' ')[1])]

        return self.pos

    def move_relative(self, x, y, transpose=True):
        if transpose:
            self.write(f'!mor {y} {x} 0')
        else:
            self.write(f'!mor {x} {y} 0')
        ret = self.read()
        ret = self.read()
        while ret == b'':
            ret = self.read()
        if not ret[:3] == '@@@':
            raise Exception(f'Tango Stage movement error: {ret}')

    def move_absolute(self, x, y, transpose=True):
        if transpose:
            self.write(f'!moa {y} {x} 0')
        else:
            self.write(f'!moa {x} {y} 0')
        ret = self.read()
        while ret == b'':
            ret = self.read()
        if not ret[:3] == '@@@':
            raise Exception(f'Tango Stage movement error: {ret}')

    def __del__(self):
        self.ser.close()


class PriorStage(Stage):

    def __init__(self):
        self.xlim = [-30000, 30000]
        self.ylim = [-30000, 30000]
        self.ser = serial.Serial('COM7', 115200, timeout=1)
        #self.steps_x, self.steps_y = self.get_steps()
        self.steps_z = self.get_focus_steps()
        self.timeout = 20
        self.set_comp_mode()

    def set_baudrate(self):
        self.write('BAUD 115')
        print(self.read())
        self.ser.baudrate = 115200

    def wait_movement(self, timeout_message):
        start = timer()
        result = ''
        while result != 'R':
            if (timer() - start) > self.timeout:
                raise Exception(timeout_message)
            result = self.read(10)
            print(result)

    def within_limits(self, x,y):
        return x>=self.xlim[0] and x<=self.xlim[1] and y>=self.ylim[0] and y<=self.ylim[1]

    def write(self, command):
        command = command.strip()+'\r'
        self.ser.write(command.encode('utf-8'))

    def read(self, bytes=0):
        line = self.ser.read_until(serial.CR)
        return line.decode('utf-8').strip()

    def LED_ON(self):
        self.write("TTL 1 1")
        if self.read(2)!='0':
            raise Exception('Failed to set Prior Stage LED On')

    def LED_OFF(self):
        self.write("TTL 1 0")
        if self.read(2)!='0':
            raise Exception('Failed to set Prior Stage LED Off')

    def get_steps(self):
        self.write('X')
        result = self.read(10)
        x,y = result.split(',')
        return np.array([int(x),int(y)])

    def get_focus_steps(self):
        self.write('RES z')
        result = self.read(10)
        return int(1/float(result))

    def get_microsteps(self):
        self.write('SS')
        res = self.read(20)
        return int(res)

    def move_absolute(self, x, y):
        if self.within_limits(x,y):
            #self.write("G {} {}".format(x * self.steps_x, y * self.steps_y))
            self.write("G {} {}".format(x, y))
            self.wait_movement(f'Failed to move Prior Stage to absolute position {x},{y}')
        else:
            raise Exception(f'Failed to move Prior Stage to absolute position {x},{y}: outside limits')

    def move_relative(self, x, y):
        current_x, current_y = self.get_position()
        if self.within_limits(current_x + x, current_y + y):
            #self.write("GR {} {}".format(x*self.steps_x, y*self.steps_y))
            self.write("GR {} {}".format(x, y))
            self.wait_movement(f'Failed to move Prior Stage to relative position {x},{y}')
        else:
            raise Exception(f'Failed to move Prior Stage to relative position {x},{y}: outside limits')

    def get_position(self):
        self.write('PS')
        line = self.read(20)
        x,y = line.split(',')
        x = int(x)#/self.steps_x
        y = int(y)#/self.steps_y
        return np.array([x,y])

    def get_focus(self):
        self.write('PZ')
        line = self.read(20)
        z = int(line)/self.steps_z
        return z

    def focus_relative(self,z):
        start = timer()
        self.write("GR 0 0 {}".format(z*self.steps_z))
        self.wait_movement(f'Failed to move Prior Stage to relative focus {z}')

    def set_focus(self, z):
        return self.focus_absolute(z)

    def focus_absolute(self, z):
        if z<-5000 or z>3800:
            raise Exception('Focus out of bounds')
        start = timer()
        self.write("GZ {}".format(z*self.steps_z))
        self.wait_movement(f'Failed to move Prior Stage to absolute focus {z}')

    def set_comp_mode(self):
        self.write('COMP 0')
        if self.read(10)!='0':
            raise Exception('Failed to set Prior Stage comp mode')

    def reset(self):
        self.write('M')
        if self.read(10)!='R':
            raise Exception('Failed to reset Prior Stage')

    def set_speed(self,speed):
        self.write('SMS {} U'.format(speed))
        if self.read(2)!='0':
            raise Exception('Failed to set Prior Stage speed')

    def set_acceleration(self,acceleration):
        self.write('SAS {} U'.format(acceleration))
        if self.read(2)!='0':
            raise Exception('Failed to set Prior Stage acceleration')

    def get_acceleration(self):
        self.write('SAS U')
        line = self.read(20)
        return float(line)

    def get_velocity(self):
        self.write('SMS U')
        line = self.read(20)
        return float(line)

    def __del__(self):
        self.ser.close()



if __name__ == '__main__':
    s = PriorStage()
    print(s.get_velocity())
    #s.set_baudrate()
    s.move_relative(-1000,0)
    t0 = timer()
    for i in range(100):
        print(s.get_position())
    print((100/timer()-t0))
    # s.write('VS 0 0')
    # print(s.read(0))
    print('done')
    #print(s.get_focus())
    # s.LED_ON()
    # time.sleep(5)
    # s.LED_OFF()
    #s.move_absolute(5715,11267)
    # time.sleep(1)
    # print(s.get_position())
    # s.move_absolute(100,100)
    # time.sleep(1)
    # print(s.get_position())
    # s.move_absolute(200,200)
    # time.sleep(1)
    # print(s.get_position())
