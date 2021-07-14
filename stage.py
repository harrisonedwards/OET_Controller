import serial
from serial.tools import list_ports


class Stage():

    def __init__(self):
        self.ser = self.find_port()
        self.pos = self.get_position()
        self.step_size = 25000
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
                print(f'did not connect stage on port {port}')

    def read_write(self, write):
        self.ser.write(str.encode(write + ' \r'))
        return self.ser.readline()

    def get_position(self):
        self.pos = self.read_write('?pos')
        return self.pos

    def move_relative(self, x=0, y=0):
        ret = self.read_write(f'mor {x} {y} 0')
        if ret != b'':
            raise Exception(f'Stage movement error: {ret}')

    def step(self, direction):
        if direction == 'l':
            self.move_relative(y=self.step_size)
        elif direction == 'r':
            self.move_relative(y=-self.step_size)
        elif direction == 'u':
            self.move_relative(x=-self.step_size)
        elif direction == 'd':
            self.move_relative(x=self.step_size)

    def move_absolute(self, x=0, y=0):
        ret = self.read_write(f'moa {x} {y} 0')
        if ret != b'':
            raise Exception(f'Stage movement error: {ret}')

    def set_xystep_size(self, value):
        print(f'xy step size set to: {value}')
        self.step_size = value

    def set_xy_speed(self, value):
        self.speed = value

    def get_xy_speed(self):
        speeds = self.read_write('?speed?')
        return speeds

    def get_xy_accels(self):
        start_accels = self.read_write('?accel').decode('utf-8')
        stop_accels = self.read_write('?stopaccel').decode('utf-8')
        xy_start_accel = start_accels.split(' ')[0]
        xy_stop_accel = stop_accels.split(' ')[0]
        return float(xy_start_accel), float(xy_stop_accel)

if __name__ == '__main__':
    s = Stage()
    # print(s.get_xy_speed())

    print(s.get_xy_accels())
    # s.move_absolute(0, 0)
