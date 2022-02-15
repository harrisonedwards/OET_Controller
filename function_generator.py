import pyvisa as visa
import logging


class FunctionGenerator():

    def __init__(self):
        # hard coded for now...for some reason ResourceManager.list_resources() hangs indefinitely
        failure = False
        try:
            self.connection = visa.ResourceManager().get_instrument('USB0::0x0957::0x0407::MY44008868::0::INSTR')
            if 'Agilent Technologies,33220A,MY44008868,2.00-2.00-22-2' in self.connection.query('*IDN?'):
                logging.info('successfully connected to function generator')
                self.change_output('OFF')
            else:
                raise Exception('failed to connect to function generator')
        except:
            logging.critical('failed to connect to function generator')

        # self.connection.write('*RST')

    def __del__(self):
        try:
            if self.connection != None:
                logging.info('closing function generator connection...')
                self.set_voltage(0)
                self.change_output(0)
                self.connection.close()
        except:
            pass

    def set_voltage(self, voltage):
        self.connection.write(f'SOURce:VOLTage:LEVel:IMMediate:AMPLitude {voltage}')
        ret = self.connection.query('VOLT?')
        logging.info(f'voltage set to {ret}')

    def set_frequency(self, frequency):
        self.connection.write(f'SOURce:FREQuency {frequency}')
        ret = self.connection.query('FREQ?')
        logging.info(f'frequency set to {ret}')

    def set_waveform(self, waveform):
        self.connection.write(f'FUNC {waveform}')
        ret = self.connection.query('FUNC?')
        logging.info(f'waveform set to {ret}')

    def change_output(self, output):
        self.connection.write(f'OUTP {output}')
        ret = self.connection.query('OUTP?')
        logging.info(f'function generator output: {ret}')

    def set_sweep_freqs(self, start, stop, time):
        self.connection.write(f'FREQ:START {start}')
        self.connection.write(f'FREQ:STOP {stop}')
        self.connection.write(f'SWE:TIME {time}')
        logging.info(f'function generator sweep set: {start} to {stop} in {time}s')

    def toggle_sweep(self, state, start, stop, time):
        self.set_sweep_freqs(start, stop, time)
        if state:
            self.connection.write('SWE:STAT ON')
        else:
            self.connection.write('SWE:STAT OFF')


if __name__ == '__main__':
    function_generator = FunctionGenerator()
    function_generator.set_voltage(2)
    function_generator.set_frequency(50)
    function_generator.set_frequency(500)
