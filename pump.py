import serial
import logging


class Pump:

    def __init__(self):
        try:
            self.ser = self.connect()
        except Exception as e:
            logging.warning('failed to connect to pump...')
            self.ser = None
        self.mode = ''
        self.statuses = [':', '>', '<', 'T*', '*']

    def __del__(self):
        if self.ser is not None:
            logging.info('closing pump connection...')
            self.ser.close()

    def connect(self):
        for i in range(1, 10):
            try:
                s = serial.Serial('COM' + str(i), baudrate=115200, stopbits=2, timeout=.25)
                s.flushInput()
                s.flushOutput()
                s.write('addr \r\n'.encode())
                r = s.read(100).decode()
                if 'Pump' in r:
                    logging.info('connected to pump')
                    return s
            except Exception as e:
                logging.warning(e)
        raise Exception('failed to connect to pump')
        logging.warning('failed to connect to pump')
        return False

    def get_response(self):
        response = ''
        while not any(item in self.statuses for item in response):
            piece = self.ser.read()
            if piece != b'':
                response += piece.decode('utf-8')
        return response

    def send_receive(self, cmd):
        try:
            self.ser.write('{} \r\n'.format(cmd).encode())
            response = self.get_response()
            # logging.info(f'cmd sent to pump: {cmd}\tresponse from pump: {response}')
            return response.replace('\n', '').replace('\r', '')
        except Exception as e:
            logging.critical(f'pump command failed: {e}')

    def re_init(self):
        self.send_receive('\r')
        self.send_receive('cvol')

    def get_pump_status(self):
        rate = self.send_receive('crate')
        return f'{rate}'

    def dispense(self, amount, rate):
        self.re_init()
        self.send_receive(f'irate {rate} ul/min')
        self.send_receive(f'tvolume {amount} ul/min')
        self.send_receive('irun')
        self.mode = 'd'

    def withdraw(self, amount, rate):
        self.re_init()
        self.send_receive(f'wrate {rate} ul/min')
        self.send_receive(f'tvolume {amount} ul/min')
        self.send_receive('wrun')
        self.mode = 'w'

    def halt(self):
        self.send_receive('stop')
