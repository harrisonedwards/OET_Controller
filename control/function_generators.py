import pyvisa as pv
import time

class Function_Generator:

    status = 'OFF'

    def __init__(self, identity, frequency=20000, amplitude=1.5, offset=0):
        self.frequency = frequency
        self.amplitude = amplitude
        self.offset = offset
        resource_manager=pv.ResourceManager()
        all_devices = resource_manager.list_resources()
        usb_devices = [d for d in all_devices if d.startswith('USB')]
        if not len(usb_devices):
            raise Exception('Cannot start Function Generator. No USB devices found. \n Perhaps you need to turn it on?')
        if len(usb_devices)>1:
            raise Exception(f'Cannot start Function Generator. Too many USB devices: {usb_devices}')
        self.FunctionGenerator=resource_manager.open_resource(usb_devices[0])
        if identity in self.identity():
            self.OFF()
        else:
            raise Exception(f'Cannot start Function Generator. USB device is not {identity}')
        
    def ON(self,freq=None, amp=None, offset=None):
        if freq is None:
            freq = self.frequency
        if amp is None:
            amp = self.amplitude
        if offset is None:
            offset = self.offset
        self.FunctionGenerator.write("OUTP OFF")
        self.FunctionGenerator.write(f"APPL:SQU {freq},{amp} VPP,{offset}")
        self.FunctionGenerator.write("OUTP ON")
        self.status = 'ON'
        print('Function Generator',self.status)

    def OFF(self):
        if self.status == 'OFF':
            return
        self.FunctionGenerator.write("OUTP OFF")
        self.status = 'OFF'
        print('Function Generator',self.status)

    def reset(self):
        self.FunctionGenerator.write("*RST;STAT:PRES;*CLS")

    def identity(self):
        return self.FunctionGenerator.query("*IDN?")

    def close(self):
        self.FunctionGenerator.close()

# Deprecated: Use WG33509B
#
# class U2761A(Function_Generator):
#
# def __init__(self, frequency=20000, amplitude=1.5, offset=0):
#     super().__init__('U2761A', frequency=frequency, amplitude=amplitude, offset=offset)

class WG33509B(Function_Generator):

    def __init__(self, frequency=20000, amplitude=1.5, offset=0):
        super().__init__('33509B', frequency=frequency, amplitude=amplitude, offset=offset)


if __name__=="__main__":
    a=WG33509B()




    







