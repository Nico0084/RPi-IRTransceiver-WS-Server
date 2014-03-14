# -*- coding: utf-8 -*-

""" This file is part of DAIKIN PAC Controler project $

License
=======

B(Rpi_IR_Transceiver} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

B{Rpi_IR_Transceiver} is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Domogik. If not, see U{http://www.gnu.org/licenses}.

Program purpose
==============

Can receive/send IR code RAW (pulse/pause pairs) and communicate with client by using WebSocket server in JSON format.

Implements
==========


"""
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error importing RPi.GPIO!  This is probably because you need superuser privileges.  You can achieve this by using 'sudo' to run your script")

import time
import threading

class RpiIRTransException(Exception):
    """"Rpi Transceiver generic exception class.
    """
    def __init__(self, value):
        """Initialisation"""
        Exception.__init__(self)
        self.msg = "Rpi Transceiver generic exception:"
        self.value = value
                                
    def __str__(self):
        """String format objet"""
        return repr(self.msg+' '+self.value)

FREQUENCIES = {38000:{"PWMClock": 2 , "PWMRange" : 252,  "DutyCycle"  : 50}}   # Parameters for 38kHz PWMClock = 2, PWMRange = 252 , DutyCycle % range for pulse to frequency

DataTypes = ["RAW", "BinTimings", "HEX"]
RAWCode = 0
BinTCode = 1
HEXCode = 2
    
class RpiIRTrans:
    '''Represente un émeteur/recepteur de signaux infrarouge RAW'''
    
    def __init__(self, manager,  pinIREmitter = 18,  pinIRReceiver = 25,  freq= 38000,  usePWM = True,  useGPIOIn = True):
        '''Initialise le transmetteur
        @param pinIREmitter: Id GPIO du pin Emetteur (output) defaut GPIO 18)
        @param pinIRReceiver: Id GPIO du pin recepteur (intput) defaut GPIO 25)
        '''
        self._manager = manager
        self.irEmitter = pinIREmitter
        self.pwmEmitter = None
        self.irReceiver = pinIRReceiver
        self.freq = freq
        self.useGPIO = useGPIOIn
        self.lockRecv = False
        self.pwmClock = 0
        self.pwmRange = 0
        self.dutyCycle = 0;
        self.setFrequency(freq)
        self.encoders = {}
        self._MemIRCode = None
        print "GPIO Board rev : {0}".format(GPIO.RPI_REVISION)
        print "GPIO version : {0}".format(GPIO.VERSION)
        GPIO.BCMInit()
        if self.useGPIO : 
            GPIO.setmode(GPIO.BCM) 
            GPIO.setup(self.irReceiver, GPIO.IN)
            GPIO.add_event_detect(self.irReceiver, GPIO.BOTH)
            GPIO.add_event_callback(self.irReceiver, self.callback_gpioEvent)
        else :
            GPIO.BCMsetModeGPIO(self.irReceiver, 0)
            th = threading.Thread(None, self.waitingEventBCM, "th_wait_for_gpio_event", (), {})
            th.daemon = True
            th.start()
        if usePWM : 
            self.pwmEmitter = GPIO.PWM2835(0, self.irEmitter, self.pwmClock, self.pwmRange)
        else :
            GPIO.BCMsetModeGPIO(self.irEmitter, 1)
            
    def __del__(self):
        GPIO.BCMClose()
        if self.useGPIO: GPIO.cleanup()
        
    def close(self):
        GPIO.BCMClose()
        if self.useGPIO: GPIO.cleanup()   
   
    def setFrequency(self, freq):
        if freq in FREQUENCIES :
            self.pwmClock = FREQUENCIES[freq]["PWMClock"]
            self.pwmRange = FREQUENCIES[freq]["PWMRange"]
            self.dutyCycle =  FREQUENCIES[freq]["DutyCycle"]
        else :
            raise RpiIRTransException("Unknown Frequency set :{0}".format(freq))
    
    def getRealFrequency(self):
        return self.pwmEmitter.GetFrequence()
        
    def register_Encoder(self,  name, encoder):
        self.encoders[name] = encoder
    
    def getEncoder(self, name):
        if name in self.encoders :
            return self.encoders[name]
        else : return None
        
    def sendIRCode(self,  encoderName, type,  irCode ):
        encoder = self.getEncoder(encoderName)
        if encoder :
            if type == DataTypes[RAWCode] :
                result = self.emitRAWIRcode(irCode)
            elif type == DataTypes[BinTCode] :
                pulsePairs = encoder.irCodeToRAW(irCode)
                if pulsePairs != [] :
                    result = self.emitRAWIRcode(encoder.irCodeToRAW(irCode))
                    if result['error'] == '': self._MemIRCode = result
                else :
                    print("IR code format error type {0} not respected.".format(type))
                    result = {"error" : "IR code format error type {0} not respected.".format(type),  "code": irCode, "encoder": ""}
            else :
                print("Code type {0} unknown".format(type))
                result = {"error" : "Code type {0} unknown".format(type),  "code": irCode, "encoder": ""}
        else :
            print("Coder {0} not registered".format(encoderName))
            result = {"error" : "Coder {0} not registered".format(encoderName),  "code": irCode, "encoder": ""}
        return result
            
    def emitRAWIRcode(self,  pulsePairs):
        self.lockRecv = True
        code = []
        codeIR = []
        if self.pwmEmitter : 
            print "Hardware pwm emit {0} pairs, freq : {1} Hz, clock {2}, range {3}, duty cycle :{4}%".format(len(pulsePairs), self.pwmEmitter.GetFrequence(), self.pwmClock, self.pwmRange, self.dutyCycle)
            codeIR = self.pwmEmitter.SendPulsePairs(pulsePairs, self.dutyCycle)
        else :
            print "Emit pulse pairs for ir code {0} pairs with software freq : 38 kHz".format(len(pulsePairs))
            codeIR = GPIO.BCMPulsePairsGPIO(pulsePairs, pOut)
        self.lockRecv = False
        for p in codeIR : code.append([int(p[0]), int(p[1])])
        result = self.rawToIRCode(code)
        if result["error"] == "" :
            print ("code DAIKIN sended :)")
        else :
            print ("Error sending code : {0}".format(result["error"]))
        print (result["code"])
        return result
    
    def rawToIRCode(self, codeIR):
        result = {"error" : "No encoder registered",  "code": ""}
        r = {"error" : "",  "code": "", "encoder": ""}
        for encoder in self.encoders :
            r = self.encoders[encoder].rawToIRCode(codeIR)
            if r["error"] == "" :
                r["encoder"] = encoder
                print ("code Identified {0} :)".format(encoder))
        if r["error"] != "" :
            result = {"error" : "No encoder finded",  "code": r["code"],   "encoder": ""}
        else : result = r
        return result
    
    def receiveRAWIRCode(self, codeIR):
        code = []
        for p in codeIR : code.append([int(p[0]), int(p[1])])
        print "Decoding code : {0} pairs".format(len(code))
        print code
        result = self.rawToIRCode(code)
        if result["error"] == "" :
            self._MemIRCode = result
            print ("code Identified :)")
        else :
            print ("Error in code : {0}".format(result["error"]))
        print (result["code"])
        self._manager.sendToWSClients(result)
    
    def getMemIRcode(self):
        if self._MemIRCode : return self._MemIRCode
        else : return {'error' : 'Unknown status', 'code': '', 'encoder': ''}
    
    def setTolerances(self, encoder,  tolerances):
        if self.encoders.has_key(encoder) :
            return self.encoders[encoder].setTolerances(tolerances)
        else :
            return {'error' : "Can't set tolerances,unknown encoder : {0}".format(encoder)}
            print "Can't set tolerances,unknown encoder : {0}".format(encoder)
        
    def getTolerances(self, encoder):
        if self.encoders.has_key(encoder) :
            return {'error' :'',  'tolerances': self.encoders[encoder].getTolerances()}
        else :
            return {'error' : "Can't get tolerances,unknown encoder : {0}".format(encoder),  'tolerances' : {}}
            print "Can't get tolerances,unknown encoder : {0}".format(encoder)
            
            
            
    def waitingEventBCM( *args,  **kwargs):
        while True :
            if not self.lockRecv :
                codeIR = GPIO.BCMWatchPulsePairsGPIO(self.irReceiver)
                if codeIR : self.receiveRAWIRCode(codeIR)
                time.sleep(0.01)
            else : time.sleep(0.5)
    
    def callback_gpioEvent(self,  GPIOPin):
        if GPIOPin == self.irReceiver :
            print"IR Receiver Event ..."
            codeIR = GPIO.BCMWatchPulsePairsGPIO(self.irReceiver)
            if codeIR : self.receiveRAWIRCode(codeIR)
        else :
            print "IR Receiver Event on bad pin : {0}".format(GPIOPin)
