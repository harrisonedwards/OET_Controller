from ctypes import *
import os

dll_name = 'MT_Polygon1000_SDK.dll'

clib = cdll.LoadLibrary(os.path.dirname(os.path.abspath(__file__)) + os.path.sep + dll_name)

print(clib.MTPLG_ConnectDev(c_int(0)))

ModuleNo = c_char_p()
print(clib.MTPLG_GetDevModuleNo(c_int(0), ModuleNo))
print(ModuleNo)