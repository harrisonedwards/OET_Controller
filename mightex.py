import os, logging
import time
from ctypes import *
import numpy as np
# from pyglet.gl import *
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
        logging.info(f'connected to DMD: {devno.value}')
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

        self.render_to_dmd(self.get_blank_image())

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
        logging.info(f'init dmd leds: {self.led_clib.MTUSB_BLSDriverInitDevices()}')
        logging.info(f'open dmd leds: {self.led_clib.MTUSB_BLSDriverOpenDevice(0)}')
        logging.info(f'reset dmd device: {self.led_clib.MTUSB_BLSDriverResetDevice(0)}')
        logging.info(f'open dmd led: {self.led_clib.MTUSB_BLSDriverOpenDevice(0)}')
        self.set_dmd_current(0)
        ret = self.led_clib.MTUSB_BLSDriverGetChannels(0)
        logging.info(f'num of led channels: {ret}')
        for channel in range(1, 4): # there are 4 total channels, but we will forget about them for now
            ret = self.led_clib.MTUSB_BLSDriverSetMode(0, channel, 1)
            logging.info(f'set led mode to enable for channel {channel}, returned: {ret}')
            # print()(f'set softstart for channel {channel}:', self.led_clib.MTUSB_BLSDriverSetMode(0, channel))
            ret = self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, channel, 1000)
            logging.info(f'set led current to 100% for channel {channel}, returned: {ret}')

    def set_dmd_current(self, current):
        current *= 10
        current = int(current)
        log_str = f'set led current to {current} for channel 1:', \
                  self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, 1, current)
        print(log_str)
        self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, 2, current)
        self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, 3, current)
        self.led_clib.MTUSB_BLSDriverSetNormalCurrent(0, 4, current)

    def toggle_dmd_light(self, state):
        print(f'set led mode to enable for channel:', self.led_clib.MTUSB_BLSDriverSetMode(0, 1, int(state)))
        print(f'set led mode to enable for channel:', self.led_clib.MTUSB_BLSDriverSetMode(0, 2, int(state)))
        print(f'set led mode to enable for channel:', self.led_clib.MTUSB_BLSDriverSetMode(0, 3, int(state)))
        print(f'set led mode to enable for channel:', self.led_clib.MTUSB_BLSDriverSetMode(0, 4, int(state)))

    def get_blank_image(self):
        offs = np.zeros((self.height, self.width * 2), dtype=np.uint8)
        return offs

    def clear_oet_projection(self):
        blank = self.get_blank_image()
        self.render_to_dmd(blank)

    def translate(self, amt, cx, cy, angle, scale, image, adding):
        amt_x, amt_y = self.pol2cart(amt, -angle * np.pi / 90)
        cx += amt_x
        cy += amt_y
        image = self.rotate_and_scale(angle, scale, image)
        cx, cy, angle = self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return cx, cy, angle

    def strafe(self, amt, cx, cy, angle, scale, image, adding):
        amt_x, amt_y = self.pol2cart(amt, (-angle * np.pi / 90) + np.pi / 2)
        cx += amt_x
        cy += amt_y
        image = self.rotate_and_scale(angle, scale, image)
        cx, cy, angle = self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return cx, cy, angle

    def turn_robot(self, amt, cx, cy, angle, scale, image, adding):
        angle += amt
        image = self.rotate_and_scale(angle, scale, image)
        cx, cy, angle = self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return cx, cy, angle

    def scale_projection(self, amt, cx, cy, angle, scale, image, adding):
        scale += amt
        image = self.rotate_and_scale(angle, scale, image)
        self.project_loaded_image(cx, cy, angle, image, adding=adding, inplace=True)
        return scale

    def rotate_and_scale(self, angle, scale, image):
        # rotate first
        image = self.rotate_image(image, angle)
        # now scale
        h, w = image.shape
        image = cv2.resize(image, (int(w * scale / 100), int(h * scale / 100)))
        # threshold to binarize
        ret, image = cv2.threshold(image, 127, 255, cv2.THRESH_BINARY)
        image = self.rotate_image(image, angle)
        return image

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
            img[start_y:start_y + cropped_projection.shape[0], start_x:start_x + cropped_projection.shape[1]] = \
                cropped_projection

        self.curr_img = img.astype(np.uint8)

        return cx, cy, angle

    def update(self):
        self.render_to_dmd(self.curr_img)

    def project_brush(self, dmd_scaled_x, dmd_scaled_y, radius, prev_scaled_x=None, prev_scaled_y=None):
        x = int(dmd_scaled_x * 912 * 2)
        y = int(dmd_scaled_y * 1140)
        if prev_scaled_x == None or prev_scaled_y == None:
            img = cv2.circle(self.curr_img, (x, y), int(radius), 255, -1)
        else:
            prev_x = int(prev_scaled_x * 912 * 2)
            prev_y = int(prev_scaled_y * 1140)
            img = cv2.line(self.curr_img, (prev_x, prev_y), (x, y), 255, int(2 * radius))
        self.render_to_dmd(img)

    def project_eraser(self, dmd_scaled_x, dmd_scaled_y, radius, prev_scaled_x=None, prev_scaled_y=None):
        x = int(dmd_scaled_x * 912 * 2)
        y = int(dmd_scaled_y * 1140)
        if prev_scaled_x == None or prev_scaled_y == None:
            img = cv2.circle(self.curr_img, (x, y), int(radius), 0, -1)
        else:
            prev_x = int(prev_scaled_x * 912 * 2)
            prev_y = int(prev_scaled_y * 1140)
            img = cv2.line(self.curr_img, (prev_x, prev_y), (x, y), 0, int(2 * radius))
        self.render_to_dmd(img)

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



        # fixing a dumb off-by-one bug...probably an easier way to do this...
        if end_x - start_x != cropped_projection.shape[1]:
            diff = abs((end_x - start_x) - cropped_projection.shape[1])
            if start_x == 0:
                end_x += diff
            elif start_x > 0:
                start_x -= diff

        if end_y - start_y != cropped_projection.shape[0]:
            diff = abs((end_y - start_y) - cropped_projection.shape[0])
            if start_y == 0:
                end_y += diff
            elif start_y > 0:
                start_y -= diff

        # final crop to ensure that it fits within the dmd...
        if cropped_projection.shape[0] > 1140:
            cropped_projection = cropped_projection[0:1140, :]
        if cropped_projection.shape[1] > 912 * 2:
            cropped_projection = cropped_projection[:, 912 * 2]

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
        data = (c_ubyte * len(image_bytes))(*image_bytes)
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
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    poly = Polygon1000(1140, 912)
    #poly.initialize_dmd()
    #poly.set_dmd_current(100)
    poly.render_to_dmd(np.ones((1140,912*2),np.uint8))
    time.sleep(10)
