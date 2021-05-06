import serial


class Pump:

    def __init__(self):
        try:
            self.ser = self.connect()
        except Exception as e:
            print('failed to connect to pump...')
            self.ser = None

    def __del__(self):
        if self.ser is not None:
            print('closing pump connection...')
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
                        print('connected to pump')
                        return s
            except Exception as e:
                print(e)
        raise Exception('failed to connect')


    def send_receive(self, cmd):
        self.ser.write('{} \r\n'.format(cmd).encode())
        return self.ser.read(100).decode()

    def dispense(self, amount, rate):
        self.send_receive('ctvolume')
        self.send_receive('cvolume')
        r = self.send_receive('irate {} ul/min'.format(rate))
        print('received:', r)
        r = self.send_receive('tvolume {} ul/min'.format(amount))
        print('received:', r)
        r = self.send_receive('irun')
        print('received:', r)

    def withdraw(self, amount, rate):
        self.send_receive('ctvolume')
        self.send_receive('cvolume')
        r = self.send_receive('wrate {} ul/min'.format(rate))
        print('received:', r)
        r = self.send_receive('tvolume {} ul/min'.format(amount))
        print('received:', r)
        r = self.send_receive('wrun')
        print('received:', r)

    def halt(self):
        r = self.send_receive('stop')
        print('received:', r)
