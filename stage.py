import serial
from serial.tools import list_ports


class Stage():

    def __init__(self):
        self.ser = self.find_port()
        self.pos = self.get_position()
        self.step_size = 0.005
        print(f'stage initial position: {self.pos}')
        self.read_write('!axis 1 1 1')
        self.read_write('!dim 2 2')
        print(self.read_write('!autostatus 2'))

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
        print(f'writing command to stage: {write}')
        self.ser.write(str.encode(write + ' \r'))
        return self.ser.readline()

    def get_position(self):
        self.pos = self.read_write('?pos')
        return self.pos

    def move_relative(self, x=0, y=0):
        ret = self.read_write(f'!mor {x} {y} 0')
        # print(ret)
        if b'OK' not in ret:
            print('warning: stage still moving...additional movement command ignored')
            # raise Exception(f'Stage movement error: {ret}')

    def halt(self):
        ret = self.read_write('!a')
        if b'OK' not in ret:
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
        if ret != b'OK...\r' and ret != b'':
            raise Exception(f'Stage movement error: {ret}')

    def set_xystep_size(self, value):
        print(f'xy step size set to: {value}')
        self.step_size = value

    def set_xy_vel(self, value):
        cmd_string = f'!vel {value} {value} {value}'
        print(f'setting velocity: {value}')
        ret = self.read_write(cmd_string)
        return ret

    def get_xy_vel(self):
        speeds = self.read_write('?vel?').decode('utf-8')
        print(f'speed: {speeds}')
        return float(speeds.split(' ')[0])

    def get_xy_accels(self):
        start_accels = self.read_write('?accel').decode('utf-8')
        stop_accels = self.read_write('?stopaccel').decode('utf-8')
        xy_start_accel = start_accels.split(' ')[0]
        xy_stop_accel = stop_accels.split(' ')[0]
        return float(xy_start_accel), float(xy_stop_accel)

    def set_xy_start_accel(self, value):
        cmd_string = f'!accel {value} {value} {value}'
        print(f'setting start acceleration: {value}')
        ret = self.read_write(cmd_string)
        return ret

    def set_xy_stop_accel(self, value):
        cmd_string = f'!stopaccel {value} {value} {value}'
        print(f'setting stop acceleration: {value}')
        ret = self.read_write(cmd_string)
        return ret

if __name__ == '__main__':
    s = Stage()
    print(s.get_xy_vel())
    print(s.set_xy_vel(2))
    print(s.get_xy_vel())
    print(s.read_write('!mor 5 0'))
    # print(s.get_xy_accels())
    # print(s.set_xy_start_accel(0.2))
    # print(s.set_xy_stop_accel(1))
    # print(s.get_xy_accels())
    # s.move_absolute(0, 0)
