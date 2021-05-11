import ctypes, time, os
from PyQt5 import QtWidgets

dll_name = 'Ni_Mic_Driver.dll'

c_lib = ctypes.cdll.LoadLibrary(os.path.dirname(os.path.abspath(__file__)) + os.path.sep + dll_name)

default_mask = ctypes.c_uint64(0xffffffffffffffff)


def get_device_list():
    device_count = ctypes.create_string_buffer(32)
    device_list = ctypes.create_string_buffer(64)
    c_lib.MIC_GetDeviceList(ctypes.byref(device_count), ctypes.pointer(device_list))
    print('device count:', device_count.value)
    print('device list:', device_list.value)
    return device_count, device_list


class MIC_Command(ctypes.Structure):
    _fields_ = [('wszCommandString', ctypes.c_wchar * 256),
                ('pCommandData', ctypes.c_void_p)]

    def __repr__(self):
        return '({0}, {1})'.format(self.wszCommandString, self.pCommandData)


def issue_dedicated_command(command, val1=None, val2=None):
    cmd = MIC_Command()
    cmd.wszCommandString = command
    if val1 or val2:
        arr = (ctypes.c_int32 * 2)(val1, val2)
        cmd.pCommandData = ctypes.c_void_p(ctypes.addressof(arr))
    data_buffer = ctypes.create_string_buffer(32)
    ret = c_lib.MIC_DedicatedCommand(ctypes.byref(cmd), data_buffer)
    if ret != 0:
        print(f'Command {command} FAILED!', ret)
    print('Command Returned:', data_buffer.value)


def print_fields(status):
    print(' '.join([f'{field_name} {getattr(status, field_name)}' for field_name, field_type in status._fields_]))


class MIC_Data(ctypes.Structure):
    _fields_ = [('uiDataUsageMask', ctypes.c_uint64),
                ('iZPOSITION', ctypes.c_int32),
                ('iZPOSITIONTolerance', ctypes.c_int32),
                ('iZPOSITIONSpeed', ctypes.c_int32),
                ('iXPOSITION', ctypes.c_int32),
                ('iYPOSITION', ctypes.c_int32),
                ('iXPOSITIONTolerance', ctypes.c_int32),
                ('iXPOSITIONSpeed', ctypes.c_int32),
                ('iYPOSITIONTolerance', ctypes.c_int32),
                ('iYPOSITIONSpeed', ctypes.c_int32),
                ('iZPIEZOPOSITION', ctypes.c_int32),
                ('iNOSEPIECE', ctypes.c_int32),
                ('iTURRET1POS', ctypes.c_int32),
                ('iTURRET1SHUTTER', ctypes.c_int32),
                ('iTURRET2POS', ctypes.c_int32),
                ('iTURRET2SHUTTER', ctypes.c_int32),
                ('iCONDENSER', ctypes.c_int32),
                ('iFILTERWHEEL_EXC', ctypes.c_int32),
                ('iFILTERWHEEL_BARRIER', ctypes.c_int32),
                ('iLIGHTPATH', ctypes.c_int32),
                ('iANALYZER', ctypes.c_int32),
                ('iSHUTTER_EPI', ctypes.c_int32),
                ('iSHUTTER_DIA', ctypes.c_int32),
                ('iSHUTTER_AUX', ctypes.c_int32),
                ('iDIALAMP_VOLTAGE', ctypes.c_int32),
                ('iDIALAMP_SWITCH', ctypes.c_int32),
                ('iDIALAMP_CTRLMODE', ctypes.c_int32),
                ('iINTENSILIGHT_POS', ctypes.c_int32),
                ('iINTENSILIGHT_SHUTTE', ctypes.c_int32),
                ('iPFS_SWITCH', ctypes.c_int32),
                ('iPFS_OFFSET', ctypes.c_int32),
                ('iPFS_STATUS', ctypes.c_int32),
                ('iTIRF_MIRROR', ctypes.c_int32),
                ('iTIRF_ANGLE', ctypes.c_int32),
                ('iOPTZOOM', ctypes.c_int32),
                ('iDIAFIELDSTOP', ctypes.c_int32),
                ('iAPERTURESTOP', ctypes.c_int32),
                ('iNDFILTER', ctypes.c_int32),
                ('iZEscape', ctypes.c_int32),
                ('iXYEscape', ctypes.c_int32)]


class Microscope():

    def __init__(self):
        self.open_microscope()
        self.status = self.get_status()
        print_fields(self.status)
        self.step_size = 5
        self.rolling = False
        # print('debug')

    def get_status(self):
        data_in = MIC_Data()
        data_in.uiDataUsageMask = default_mask
        ret = c_lib.MIC_DataGet(ctypes.byref(data_in))
        if ret != 0:
            print('get_status failed!', 0)
            self.close_microscope()
        return data_in

    def open_microscope(self):
        device_index = ctypes.c_int32(0)
        accessories_mask = ctypes.c_uint64()
        error_message_size = ctypes.c_int32(2 ** 32)
        error_message = ctypes.c_wchar_p()
        print('attempting connection to microscope...')
        ret = c_lib.MIC_Open(device_index,
                             ctypes.byref(accessories_mask),
                             error_message_size,
                             error_message)
        if ret != 0:
            raise Exception('failed to connect')
        else:
            print('connected to microscope')

        # print('accessories mask:', accessories_mask.value)
        # print('connection error message:', error_message.value)

    def close_microscope(self):
        print('closing microscope...', c_lib.MIC_Close())

    def set_zstep_size(self, value):
        print(f'z step size set to: {value}')
        self.step_size = value

    def move_absolute_z(self, z=-500000):
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000000001

        data_in.iZPOSITION = z
        data_in.iZPOSITIONTolerance = 10
        data_in.iZPOSITIONSpeed = 1

        data_out = MIC_Data()
        data_out.uiDataUsageMask = default_mask

        try:
            ret = c_lib.MIC_DataSet(ctypes.byref(data_in),
                                    ctypes.byref(data_out),
                                    False)
            if ret != 0:
                print('microscope error!', ret)
        except Exception as e:
            print('Microscope movement error:', e)
            self.close_microscope()
        self.status = data_out
        print(f'z at: {self.status.iZPOSITION}')
        # print_fields(data_in)
        # print_fields(data_out)

    def set_turret_pos(self, pos, t1shutter, diashutter):
        status = self.get_status()
        print('turret pos:', status.iTURRET1POS,
              'turret shutter:', status.iTURRET1SHUTTER,
              'dia status:', status.iSHUTTER_DIA)
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000000040 | 0x0000000000000080 | 0x0000000000010000 | 0x0000000000000020
        data_in.iTURRET1POS = pos
        data_in.iTURRET1SHUTTER = t1shutter
        data_in.iSHUTTER_DIA = diashutter
        data_in.iNOSEPIECE = 5
        self.issue_command(data_in)

    def roll_z(self, direction):
        while self.rolling:
            time.sleep(0.02)
            QtWidgets.QApplication.processEvents()
            if direction == 'f':
                self.move_rel_z(self.step_size)
            elif direction == 'b':
                self.move_rel_z(-self.step_size)
            print('rolling...', self.status.iZPOSITION)

    def move_rel_z(self, amount):
        z = self.status.iZPOSITION
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000000001
        data_in.iZPOSITION = int(z) + int(amount)
        # data_in.iZPOSITIONTolerance = 10
        # data_in.iZPOSITIONSpeed = 1
        self.issue_command(data_in)

    def set_dia_shutter(self, state):
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000010000
        data_in.iSHUTTER_DIA = state
        self.issue_command(data_in)

    def set_filter(self, filter):
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000000040
        data_in.iTURRET1POS = filter
        self.issue_command(data_in)

    def set_objective(self, objective):
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000000020
        data_in.iNOSEPIECE = objective
        self.issue_command(data_in)

    def set_turret_shutter(self, state):
        if state == 2: state = 1
        # print('state', state)
        data_in = MIC_Data()
        data_in.uiDataUsageMask = 0x0000000000000080
        data_in.iTURRET1SHUTTER = state
        self.issue_command(data_in)

    def issue_command(self, data_in):
        data_out = MIC_Data()
        data_out.uiDataUsageMask = default_mask
        try:
            ret = c_lib.MIC_DataSet(ctypes.byref(data_in),
                                    ctypes.byref(data_out),
                                    False)
            if ret != 0:
                print('microscope error!', ret)
        except Exception as e:
            print('Microscope movement error:', e)
            self.close_microscope()
        self.status = data_out
        # print(data_out.iTURRET1POS, data_out.iTURRET1SHUTTER, data_in.iSHUTTER_DIA)


if __name__ == '__main__':
    scope = Microscope()
    # scope.set_z(-500000)
    scope.set_turret_pos(3, 1, 0)
    # scope.set_objective(1)
    scope.close_microscope()
    time.sleep(3)
