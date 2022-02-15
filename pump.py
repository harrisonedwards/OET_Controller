import serial
import logging

class Pump:

    def __init__(self):
        try:
            self.ser = self.connect()
        except Exception as e:
            logging.warning('failed to connect to pump...')
            self.ser = None

    def __del__(self):
        if self.ser is not None:
            logging.info('closing pump connection...')
            self.ser.close()

    def connect(self):
        for i in range(1,10):
            try:
                s = serial.Serial('COM' + str(i), timeout=.25)
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


    def send_receive(self, cmd):
        self.ser.write('{} \r\n'.format(cmd).encode())
        return self.ser.read(100).decode()

    def dispense(self, amount, rate):
        self.send_receive('ctvolume')
        self.send_receive('cvolume')
        r = self.send_receive('irate {} ul/min'.format(rate))
        logging.info(f'received: {r}')
        r = self.send_receive('tvolume {} ul/min'.format(amount))
        logging.info(f'received: {r}')
        r = self.send_receive('irun')
        logging.info(f'received: {r}')

    def withdraw(self, amount, rate):
        self.send_receive('ctvolume')
        self.send_receive('cvolume')
        r = self.send_receive('wrate {} ul/min'.format(rate))
        logging.info(f'received: {r}')
        r = self.send_receive('tvolume {} ul/min'.format(amount))
        logging.info(f'received: {r}')
        r = self.send_receive('wrun')
        logging.info(f'received: {r}')

    def halt(self):
        r = self.send_receive('stop')
        logging.info(f'received: {r}')