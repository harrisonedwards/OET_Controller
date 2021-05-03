import pyvisa as visa


class FunctionGenerator():

    def __init__(self):
        # hard coded for now...for some reason ResourceManager.list_resources() hangs indefinitely
        self.connection = visa.ResourceManager().get_instrument('USB0::0x0957::0x0407::MY44008868::0::INSTR')
        # self.connection.write('*RST')
        if 'Agilent Technologies,33220A,MY44008868,2.00-2.00-22-2' in self.connection.query('*IDN?'):
            print('successfully connected to function generator')
        else:
            raise Exception('failed to connect to function generator')

    def set_voltage(self, voltage):
        self.connection.write(f'SOURce:VOLTage:LEVel:IMMediate:AMPLitude {voltage}')
        ret = self.connection.query('VOLT?')
        print(f'voltage set to {ret}')

    def set_frequency(self, frequency):
        self.connection.write(f'SOURce:FREQuency {frequency}')
        ret = self.connection.query('FREQ?')
        print(f'frequency set to {ret}')


if __name__ == '__main__':
    function_generator = FunctionGenerator()
    function_generator.set_voltage(2)
    function_generator.set_frequency(50)
    function_generator.set_frequency(500)
