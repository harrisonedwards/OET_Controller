# -*- coding: utf-8 -*-
"""
Created on Sun Nov 22 10:18:04 2020

@author: XT-XT
"""

from telnetlib import Telnet
import time
        
class PJcommand():
    BrightnessDown=[0x06,0x14,0x00,0x04,0x00,0x34,0x12,0x03,0x00,0x61]
    BrightnessUP=[0x06,0x14,0x00,0x04,0x00,0x34,0x12,0x03,0x01,0x62]
    BrightnessStatus=[0x07,0x14,0x00,0x05,0x00,0x34,0x00,0x00,0x12,0x03,0x62]
    NewLine = [0x0D,0x0A]

class Projector():

    def __init__(self):
        self.telnet = TelnetClient("10.10.10.10",4661,5)

    def getBrightness(self):
        self.telnet.send_command(PJcommand.BrightnessStatus)
        ret = self.telnet.read()
        return int(bin(int.from_bytes(ret,'big'))[-8:],2)-24

    def increaseBrightness(self):
        self.telnet.send_command(PJcommand.BrightnessUP)
        ret = self.telnet.read()

    def decreaseBrightness(self):
        self.telnet.send_command(PJcommand.BrightnessDown)
        ret = self.telnet.read()

    def setBrightness(self,value):
        if value<0 or value>100:
            raise Exception('Invalid projector brightness set')
        brightness = self.getBrightness()
        while brightness!=value:
            if brightness<value:
                self.increaseBrightness()
            else:
                self.decreaseBrightness()
            #time.sleep(0.2)
            brightness = self.getBrightness()
        time.sleep(0.2)

class TelnetClient():
    #initialize
    def __init__(self,host_ip,port,timeout):
        self.host_ip=host_ip
        self.port=port
        self.timeout=timeout
        self.Tnet=Telnet(host_ip,port,timeout)
        
    #connect to projector
    def connect_host(self):
        try :
            self.Tnet.open(self.host_ip,self.port,self.timeout)
            print("Connection Success!")
        except:
            print("Connect Error!")
       
    # def login_host(username,password,timeout):
    #     self.Tnet.read_until(b"login:",timeout)
    #     self.Tnet.write(username.encode("ASCII")+b'\n')
    #     self.Tnet.read_until(b"Password:",timeout)
    #     self.Tnet.write(password.encode("ASCII")+b'\n')
    #     time.sleep(2)
    #     login_result=self.Tnet.read_very_eager().decode("ASCII")
    #     if "Login incorrect"in login_result:
    #         print("Login Error!")
    #         return False
    #     else:
    #         print("Login Success!")
    #         return True
    
    #send command to host
    def send_command(self,command):
        self.Tnet.write(bytes(command+PJcommand.NewLine))
    
    #receive result from host
    def read(self):
        val = self.Tnet.read_some()
        return val
        #time.sleep(2)
        
    #close the connection
    def telnet_close(self):
        self.Tnet.close()
    
    
if  __name__=="__main__":
    projector = Projector()
    projector.setBrightness(70)
    #print(projector.getBrightness())