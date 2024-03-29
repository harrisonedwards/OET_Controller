import serial
import logging


DEFAULT_INTENSITY = 5

class FluorescenceController():

    def __init__(self, parent=None):
        try:
            self.ser = self.get_connection()
            self.lamp_index = 0
            self.current_intensity = DEFAULT_INTENSITY
            self.change_intensity(DEFAULT_INTENSITY)
            self.turn_all_off()
        except Exception as e:
            logging.critical('failed to connect to fluorescence controller')
            self.ser = None

        # logging.info(self.send_receive('lh?'))
        # logging.info(self.send_receive(('ip=' + ','.join(['500' for i in range(4)]))))

    # having a del function messes everything up for some reason...
    # def __del__(self):
    #     try:
    #         if self.ser is not None:
    #                 self.turn_all_off(suppress_msg=True)
    #                 self.ser.reset_input_buffer()
    #                 self.ser.reset_output_buffer()
    #                 logging.info('closing fluorescence controller connection...')
    #                 self.ser.close()
    #     except Exception as e:
    #         pass

    def get_connection(self):
        possible_coms = range(1, 11)
        for com in possible_coms:
            try:
                com = f'COM{com}'
                parity = serial.PARITY_NONE
                ser = serial.Serial(com, 19200, timeout=.25,
                                    parity=parity)
                ser.write('co\r'.encode('utf-8'))
                response = ser.readline()
                # logging.info('response:', response)
                ser.write('sn?\r'.encode('utf-8'))
                response = ser.readline()
                if response == b'548\r':
                    logging.info('fluorescence controller found on {}'.format(com))
                    return ser
            except Exception as e:
                logging.warning('failed to send commands to fluorescence controller')
        raise Exception('failed to connect')
        # sys.exit(1)

    def get_response(self):
        response = ''
        while '\r' not in response:
            piece = self.ser.read()
            if piece != b'':
                response += piece.decode('utf-8')
        logging.info('response received from excitation lamp:{}'.format(response))
        return response

    def issue_command(self, command, suppress_msg=False):
        command_string = '{}\r'.format(command)
        if not suppress_msg:
            logging.info('sending command to excitation lamp:{}'.format(command_string))
        self.ser.write(command_string.encode('utf-8'))

    def send_receive(self, command, suppress_msg=False):
        self.issue_command(command, suppress_msg)
        response = self.get_response()
        return response

    def turn_led_on(self):
        self.send_receive('on=a')
        self.send_receive('on?')
        self.send_receive('ip?')

    def turn_all_off(self, suppress_msg=False):
        self.send_receive('of=a', suppress_msg)
        self.send_receive('on?')

    def change_fluorescence(self, index):
        self.turn_all_off()
        self.lamp_index = index
        self.change_intensity(self.current_intensity)
        if index == 0:
            self.turn_all_off()
        elif index in range(1, 7):
            self.turn_led_on(index)
        elif index == 7:
            self.turn_all_on()

    def change_intensity(self, intensity):
        self.current_intensity = intensity
        intensity *= 10
        cmd_string = 'ip=' + ',' * (self.lamp_index - 1) + str(int(intensity))
        self.send_receive(cmd_string)
        self.send_receive('ip?')
        self.send_receive('on=a')

    def turn_all_on(self):
        self.send_receive('ip=' + ','.join([str(self.current_intensity) for _ in range(6)]))
        self.send_receive('on=a')
        self.send_receive('on?')

    # def flush_and_close(self):
    #     logging.info('CLOSING')
    #     del self


if __name__ == '__main__':
    fluorescence = FluorescenceController()
    fluorescence.turn_all_off()
    # fluorescence.flush_and_close()
    # parity = serial.PARITY_NONE
    # ser = serial.Serial('COM3', 19200, timeout=.25,
    #                     parity=parity)
    # ser.write(b'sn?\r')
    # logging.info(ser.readline())