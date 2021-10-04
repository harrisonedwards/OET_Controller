import os
from ctypes import *
import numpy as np
from pyglet.gl import *
import cv2
from PyQt5 import QtCore, QtWidgets
import matplotlib.pyplot as plt


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
        self.circle_radius = 25
        self.tog = False
        self.controllable_projections = {}
        self.curr_img = self.get_blank_image()

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
        print(f'connected to DMD: {devno.value}')
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

    def __del__(self):
        for channel in range(1, 2):
            print(f'set led current to 0 for channel: {channel}:',
                  self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, channel, 0))
            print(f'set led mode to disable for channel {channel}:',
                  self.led_clib.MTUSB_BLSDriverSetMode(0, channel, 0))
        print('close leds:', self.led_clib.MTUSB_BLSDriverCloseDevice(0))
        print('closing DMD connection:', self.dmd_clib.MTPLG_DisconnectDev(c_int(self.dev_id)),
              self.dmd_clib.MTPLG_UnInitDevice())

    def initialize_dmd(self):
        print('init dmd leds:', self.led_clib.MTUSB_BLSDriverInitDevices())
        print('open dmd leds:', self.led_clib.MTUSB_BLSDriverOpenDevice(0))
        print('reset dmd device:', self.led_clib.MTUSB_BLSDriverResetDevice(0))
        print('open dmd led:', self.led_clib.MTUSB_BLSDriverOpenDevice(0))
        self.set_dmd_current(0)
        # print('get led channels:', self.led_clib.MTUSB_BLSDriverGetChannels(0))
        # for channel in range(1, 2): # there are 4 total channels, but we will forget about them for now
        #     print(f'set led mode to enable for channel {channel}:', self.led_clib.MTUSB_BLSDriverSetMode(0, channel, 1))
        #     # print(f'set softstart for channel {channel}:', self.led_clib.MTUSB_BLSDriverSetMode(0, channel))
        #     print(f'set led current to 100% for channel {channel}:',
        #           self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, channel, 1000))

    def set_dmd_current(self, current):
        current *= 10
        current = int(current)
        print(f'set led current to {current} for channel 1:',
              self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, 1, current))

    def toggle_dmd_light(self, state):
        print(f'set led mode to enable for channel:', self.led_clib.MTUSB_BLSDriverSetMode(0, 1, int(state)))

    def get_blank_image(self):
        offs = np.zeros((self.height, self.width * 2), dtype=np.uint8)
        return offs

    def clear_oet_projection(self):
        blank = self.get_blank_image()
        self.render_to_dmd(blank)


    def scale_projection(self, scale):
        h, w = self.projection_image.shape
        self.projection_image = cv2.resize(self.projection_image, (int(w * scale), int(h * scale)))

        # threshold to binarize
        ret, self.projection_image = cv2.threshold(self.projection_image, 127, 255, cv2.THRESH_BINARY)

        # re-project the image in the location it was in
        self.project_loaded_image(self.cx, self.cy, inplace=True)

    @staticmethod
    def pol2cart(rho, phi):
        x = rho * np.cos(phi)
        y = rho * np.sin(phi)
        return x, y

    @staticmethod
    def rotate_image(image, angle):
        image_center = tuple(np.array(image.shape[1::-1]) / 2)
        rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
        result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
        return result

    def translate(self, amt, cx, cy, angle, image, adding):
        amt_x, amt_y = self.pol2cart(amt, -angle*np.pi/180)
        cx += amt_x
        cy += amt_y
        image = self.rotate_image(image, angle)
        cx, cy, angle = self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return cx, cy, angle

    def strafe(self, amt, cx, cy, angle, image, adding):
        amt_x, amt_y = self.pol2cart(amt, (-angle*np.pi/180) + np.pi / 2)
        cx += amt_x
        cy += amt_y
        image = self.rotate_image(image, angle)
        cx, cy, angle = self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return cx, cy, angle

    def rotate_projection_image(self, rotation, cx, cy, angle, image, adding):
        angle -= rotation
        image = self.rotate_image(image, angle)
        ret, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        cx, cy, image = self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return cx, cy, angle

    def project_loaded_image(self, dmd_scaled_x, dmd_scaled_y, angle, image, adding=False, inplace=False):

        if inplace:
            # if we are moving something in place (i.e. not from a mouse click)
            cx = int(dmd_scaled_x)
            cy = int(dmd_scaled_y)
        else:
            # if we are placing something initially with a mouse click:
            cx = int(dmd_scaled_x * 912 * 2)
            cy = int(dmd_scaled_y * 1140)
            angle = 0

        img = self.get_blank_image()

        # retrieve where the image should be placed, and what it looks like cropped
        start_x, end_x, start_y, end_y, cropped_projection = self.get_crop(image, cx, cy)

        if adding:
            img[start_y:end_y, start_x:end_x] = cropped_projection
            img = np.logical_or(img, self.curr_img)
        else:
            img[start_y:end_y, start_x:end_x] = cropped_projection

        self.curr_img = img

        return cx, cy, angle

    def update(self):
        self.render_to_dmd(self.curr_img)

    def project_circle(self, dmd_scaled_x, dmd_scaled_y):
        cx = int(dmd_scaled_x * 912 * 2)
        cy = int(dmd_scaled_y * 1140)
        offs = self.get_blank_image()
        img = cv2.circle(offs, (cx, cy), self.circle_radius, 255, -1)
        self.render_to_dmd(img)
        self.cx = cx
        self.cy = cy

    def get_crop(self, projection_image, cx, cy):
        # project as much of the image as possible, and clip as necessary to fit within the dmd working area
        img = self.get_blank_image()
        h, w = projection_image.shape

        cropped_projection = np.copy(projection_image)

        start_x = cx - w // 2
        end_x = cx + w // 2
        start_y = cy - h // 2
        end_y = cy + h // 2

        if start_x < 0:
            cropped_projection = cropped_projection[:, w // 2 - cx:]
            start_x = 0
        if start_y < 0:
            cropped_projection = cropped_projection[h // 2 - cy:, :]
            start_y = 0
        if end_x > img.shape[1]:
            cropped_projection = cropped_projection[:, :w // 2 + int(img.shape[1] - cx)]
            end_x = img.shape[1]
        if end_y > img.shape[0]:
            cropped_projection = cropped_projection[:h // 2 + int(img.shape[0] - cy), :]
            end_y = img.shape[0]

        if end_x - start_x < cropped_projection.shape[1]:
            start_x -= 1
        if end_y - start_y < cropped_projection.shape[0]:
            start_y -= 1

        return start_x, end_x, start_y, end_y, cropped_projection

    def project_calibration_image(self):
        offs = self.get_blank_image()

        img = cv2.circle(offs, (0, 0), 25, 255, -1)
        img = cv2.circle(img, (912 * 2, 0), 25, 255, -1)
        img = cv2.circle(img, (912 * 2, 1140), 25, 255, -1)

        self.render_to_dmd(img)

    def render_to_dmd(self, img):
        self.curr_img = np.copy(img)
        img = img[:, 0::2]
        img = np.rot90(np.rot90(img))
        img = np.copy(img).T.flatten()
        image_bytes = np.packbits(img).tobytes()
        data = (c_byte * len(image_bytes))(*image_bytes)
        self.dmd_clib.MTPLG_SetDevStaticImageFromMemory(c_int(self.dev_id), byref(data), c_int(1))

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


if __name__ == '__main__':
    poly = Polygon1000(100, 100)
    poly.initialize_dmd()
