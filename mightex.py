import os
from ctypes import *
import numpy as np
from pyglet.gl import *
import cv2


class Polygon1000():
    class tDevTrigSetting(Structure):
        _fields_ = [('Enabled', c_int),
                    ('TrigDelay', c_int),
                    ('TrigPulseWidth', c_int),
                    ('TrigEdge', c_int),
                    ('Reserved', c_int)]

    trigger_settings = tDevTrigSetting()
    trigger_settings.Enabled = 0
    trigger_settings.TrigDelay = 0
    trigger_settings.TrigPulseWidth = 1000
    trigger_settings.TrigEdge = 2
    trigger_settings.Reserved = 0

    buffer = 0

    dmd_dll_name = 'MT_Polygon1000_SDK.dll'
    led_dll_name = 'Mightex_BLSDriver_SDK.dll'
    dll_path = r'C:\Program Files\Mightex\PolyScan2'

    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.tog = False

        numpy_image = np.zeros((self.height, self.width), dtype=bool)
        numpy_image[::2] = True
        self.image_bytes1 = np.packbits(numpy_image).tobytes()

        numpy_image = np.zeros((self.height, self.width), dtype=bool)
        self.image_bytes2 = np.packbits(numpy_image).tobytes()

        self.buff1 = (c_byte * len(self.image_bytes1))(*self.image_bytes1)
        self.buff2 = (c_byte * len(self.image_bytes1))(*self.image_bytes1)
        self.byte_buff = (c_byte * (self.height * self.width))()
        self.numpy_buff = np.zeros((self.height * self.width), dtype=np.uint8)

        current_dir = os.getcwd()
        os.chdir(self.dll_path)
        self.dmd_clib = cdll.LoadLibrary(os.path.join(self.dll_path, self.dmd_dll_name))
        self.led_clib = cdll.LoadLibrary(os.path.join(self.dll_path, self.led_dll_name))

        self.mask = np.zeros((self.width, self.height), dtype=bool)
        for h in range(self.width):
            if h % 2:
                self.mask[h] = True
            # else:
            #     self.mask[h,1::2] = True
        self.mask = self.mask.flatten()

        # try:
        #     ret = self.led_clib.MTUSB_BLSDriverInitDevices(c_int(0))
        #     print('led devices:', ret)
        #     self.led_handle = self.led_clib.MTUSB_BLSDriverOpenDevice(c_int(0))
        #     print('led connection:', self.led_handle)
        #     channel = self.led_clib.MTUSB_BLSDriverGetChannels(self.led_handle)
        #     print('led channel:', channel)
        #     for i in range(1, 5):
        #         ret = self.led_clib.MTUSB_BLSDriverSetMode(self.led_handle, c_int(i), c_int(1))
        #         print('led mode:', ret)
        #         ret = self.led_clib.MTUSB_BLSDriverSetNormalCurrent(self.led_handle, c_int(i), c_int(50))
        #         print('led current:', ret)
        # except Exception as e:
        #     print('failure to connect to DMD LED:', e)

        uninit = self.dmd_clib.MTPLG_UnInitDevice()
        if uninit != 0:
            raise Exception('Unable to uninitialise Polygon 1000')
        # SDK_API MTPLG_InitDevice(int DeviceCount, int* DevIPs);
        self.dev_id = self.dmd_clib.MTPLG_InitDevice(c_int(-1))
        if self.dev_id < 0:
            raise Exception('Unable to initialise Polygon 1000')
        connect_status = self.dmd_clib.MTPLG_ConnectDev(c_int(self.dev_id))
        if connect_status != 0:
            raise Exception('Unable to connect to Polygon 1000')
        devno = create_string_buffer(50)
        device_no_status = self.dmd_clib.MTPLG_GetDevModuleNo(c_int(self.dev_id), devno)
        if device_no_status != 0:
            raise Exception('Unable to get Polygon 1000 device number')
        print(devno.value)
        set_display_mode = self.dmd_clib.MTPLG_SetDevDisplayMode(c_int(self.dev_id), c_int(1))
        if set_display_mode != 0:
            raise Exception('Unable to set Polygon 1000 display mode')
        stop_pattern_status = self.dmd_clib.MTPLG_StopPattern(c_int(self.dev_id))
        if stop_pattern_status != 0:
            raise Exception('Unable to stop Polygon 1000 pattern')
        set_trigger_status = self.dmd_clib.MTPLG_SetDevTrigSetting(c_int(self.dev_id), self.trigger_settings)
        if set_trigger_status != 0:
            raise Exception('Unable to set Polygon 1000 trigger settings')
        self.dmd_clib.MTPLG_SetDevStaticImageFromMemory(c_int(self.dev_id), byref(self.buff1), c_int(1))
        # os.chdir(current_dir)

    def draw_pyglet(self):

        glReadPixels(0, 0, self.width, self.height, GL_LUMINANCE, GL_UNSIGNED_BYTE, self.byte_buff)

        # self.numpy_buff[::2] = np.frombuffer(self.byte_buff, dtype=np.uint8)
        # self.numpy_buff[1::2] = np.frombuffer(self.byte_buff, dtype=np.uint8)

        data = (c_byte * len(self.image_bytes1))(
            *np.packbits(np.reshape(np.frombuffer(self.byte_buff, dtype=np.uint8), (self.height, self.width)
                                    ).T.flatten()[self.mask]).tobytes()
        )
        # data = (c_byte*len(self.image_bytes1))(*self.image_bytes1)
        self.dmd_clib.MTPLG_SetDevStaticImageFromMemory(c_int(self.dev_id), byref(data), c_int(1))

    def set_image(self, image):
        offs = np.zeros((self.height, self.width), dtype=bool)
        ons = np.ones((self.height, self.width), dtype=bool)
        image = cv2.resize(image, (self.width, self.height))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        img = np.where(image != 0, ons, offs)

        self.image_bytes1 = np.packbits(img).tobytes()
        self.buff1 = (c_byte * len(self.image_bytes1))(*self.image_bytes1)



        print('changing dmd:', self.tog,
              self.dmd_clib.MTPLG_SetDevStaticImageFromMemory(c_int(self.dev_id), byref(self.buff1), c_int(1)))

# if __name__ == '__main__':
#     poly = Polygon1000()
# while True:
#     poly.draw_pyglet()