import serial, logging
from serial.tools import list_ports


class Stage():

    def __init__(self):
        self.ser = self.find_port()
        self.pos = self.get_position()
        self.step_size = 0.005
        logging.info(f'stage initial position: {self.pos}')
        self.read_write('!axis 1 1 1')
        self.read_write('!dim 2 2')
        logging.info(self.read_write('!autostatus 2'))

    def find_port(self):
        for port in list_ports.comports():
            try:
                ser = serial.Serial(port.device, 57600, timeout=0.2)
                ser.write(b'?version \r')
                r = ser.readline()
                if b'TANGO' in r:
                    logging.info(f'stage found on port {port}')
                    return ser
            except Exception as e:
                logging.info(f'did not connect stage on port {port}')

    def read_write(self, write):
        # logging.info(f'writing command to stage: {write}')
        self.ser.write(str.encode(write + ' \r'))
        ret = self.ser.readline()
        # logging.info(f'response received from stage: {ret}')
        return ret

    def get_position(self):
        self.pos = self.read_write('?pos')
        return self.pos

    def move_relative(self, x=0, y=0):
        try:
            ret = self.read_write(f'!mor {x} {y} 0')
            if b'OK' not in ret:
                logging.warning('stage still moving...additional movement command ignored')
        except Exception as e:
            logging.CRITICAL(f'stage movement failure: {e}')

    def halt(self):
        ret = self.read_write('!a')
        if b'OK' not in ret:
            logging.critical('stage halt error')

    def step(self, direction):
        if direction == 'l':
            self.move_relative(y=self.step_size)
        elif direction == 'r':
            self.move_relative(y=-self.step_size)
        elif direction == 'u':
            self.move_relative(x=-self.step_size)
        elif direction == 'd':
            self.move_relative(x=self.step_size)

    def move_absolute(self, x=0.0, y=0.0):
        try:
            # print(f'!moa {x} {y} 0')
            ret = self.read_write(f'!moa {x} {y} 0')
            if 'OK...' not in ret.decode():
                logging.warning(f'Stage movement error: {ret}')
        except Exception as e:
            logging.CRITICAL(f'stage movement failure: {e}')

    def set_xystep_size(self, value):
        logging.info(f'xy step size set to: {value}')
        self.step_size = value

    def set_xy_vel(self, value):
        cmd_string = f'!vel {value} {value} {value}'
        logging.info(f'setting velocity: {value}')
        ret = self.read_write(cmd_string)
        return ret

    def get_xy_vel(self):
        speeds = self.read_write('?vel?').decode('utf-8')
        logging.info(f'speed: {speeds}')
        return float(speeds.split(' ')[0])

    def get_xy_accels(self):
        start_accels = self.read_write('?accel').decode('utf-8')
        stop_accels = self.read_write('?stopaccel').decode('utf-8')
        xy_start_accel = start_accels.split(' ')[0]
        xy_stop_accel = stop_accels.split(' ')[0]
        return float(xy_start_accel), float(xy_stop_accel)

    def set_xy_start_accel(self, value):
        cmd_string = f'!accel {value} {value} {value}'
        logging.info(f'setting stage start acceleration: {value}')
        ret = self.read_write(cmd_string)
        return ret

    def set_xy_stop_accel(self, value):
        cmd_string = f'!stopaccel {value} {value} {value}'
        logging.info(f'setting stage stop acceleration: {value}')
        ret = self.read_write(cmd_string)
        return ret

if __name__ == '__main__':
    s = Stage()
    print(s.read_write('!moa -2.944500 -18.226101 0'))
    # s.move_absolute(-2.944500, -18.226101)
    import time
    time.sleep(5)
    print(s.get_position())
    print(s.read_write('?dim'))
    # logging.info(s.get_xy_vel())
    # logging.info(s.set_xy_vel(2))
    # logging.info(s.get_xy_vel())
    # logging.info(s.read_write('!mor 5 0'))
    # logging.info(s.get_xy_accels())
    # logging.info(s.set_xy_start_accel(0.2))
    # logging.info(s.set_xy_stop_accel(1))
    # logging.info(s.get_xy_accels())
    # s.move_absolute(0, 0)
