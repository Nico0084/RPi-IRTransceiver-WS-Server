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
import os

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
    
    def __init__(self, manager,  pinIREmitter = 18,  pinIRReceiver = 25, pinIRAck = 17, freq = 38000,  usePWM = True,  useGPIOIn = True):
        '''Initialise le transmetteur
        @param pinIREmitter: Id GPIO du pin Emetteur (output) defaut GPIO 18)
        @param pinIRReceiver: Id GPIO du pin recepteur (intput) defaut GPIO 25)
        @param pinIRAck: Id GPIO du pin for ack send (intput) defaut GPIO 17)
        '''
        self._manager = manager
        self.irEmitter = pinIREmitter
        self.pwmEmitter = None
        self.irReceiver = pinIRReceiver
        self.freq = freq
        self.irAck = pinIRAck
        self.useGPIO = useGPIOIn
        self.lockRecv = False
        self.pwmClock = 0
        self.pwmRange = 0
        self.dutyCycle = 0;
        self.setFrequency(freq)
        self.encoders = {}
        self._MemIRCode = None
        self.ackState = 0
        self.tLastAck = time.time()
        self.waitAck = 0
        self._fileBackup = "/var/local/irtranslast.txt"
        print "GPIO Board rev : {0}".format(GPIO.RPI_REVISION)
        print "GPIO version : {0}".format(GPIO.VERSION)
        GPIO.BCMInit()
        if self.useGPIO :
            GPIO.setmode(GPIO.BCM) 
            GPIO.setup(self.irReceiver, GPIO.IN)
            GPIO.add_event_detect(self.irReceiver, GPIO.BOTH)
            GPIO.add_event_callback(self.irReceiver, self.callback_gpioEvent)
            print "GPIO {0} Input IR receiver ready\n".format(self.irReceiver)           
            GPIO.setup(self.irAck, GPIO.IN, pull_up_down= GPIO.PUD_DOWN)
            GPIO.add_event_detect(self.irAck, GPIO.RISING)#, bouncetime = 200)
            GPIO.add_event_callback(self.irAck, self.callback_gpioAck)
            self.ackState = GPIO.input(self.irAck)
            print "GPIO {0} Input ACK ready, state : {1}\n".format(self.irAck, self.ackState)         
        else :
            print "BCM {0} Input ready\n".format(self.irReceiver)
            GPIO.BCMsetModeGPIO(self.irReceiver, 0)
            th = threading.Thread(None, self.waitingEventBCM, "th_wait_for_gpio_event", (), {})
            th.daemon = True
            th.start()
        if usePWM : 
            self.pwmEmitter = GPIO.PWM2835(0, self.irEmitter, self.pwmClock, self.pwmRange)
        else :
            GPIO.BCMsetModeGPIO(self.irEmitter, 1)
        self.readIRCodeFile()
            
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
                    if result['error'] == '': 
                        self._MemIRCode = result
                        self.writeIRCodeFile()
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
        self.waitAck = time.time()
        for p in codeIR : code.append([int(p[0]), int(p[1])])
        result = self.rawToIRCode(code)
        if result["error"] == "" :
            print ("code DAIKIN sended :)")
        else :
            print ("Error sending code : {0}".format(result["error"]))
        print (result["code"])
        time.sleep(1)
        if not self.waitAck :
            print "((((((( good ack )))))))"
            result = self.rawToIRCode(pulsePairs)
        else :
            print "!!!!! no ack !!!!!"
            if result["error"] == "" :
                result["error"]  = "No hardware ack."
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
#        print code
        result = self.rawToIRCode(code)
        if result["error"] == "" :
            print ("code Identified :)")
        else :
            print ("Error in code : {0}".format(result["error"]))
        print (result["code"])
        hardAck = True
        while self.waitAck:
            if time.time() - self.waitAck > 3.5:
                self.waitAck = 0
                hardAck = False
            else : time.sleep(0.1)
        if hardAck:
            print "======= Ack receiver OK ======"
            self._MemIRCode = result
            self.writeIRCodeFile()
            self._manager.sendToWSClients(result)
        else :
            print "---- No hard Ack receiver for code received ----"
    
    def getMemIRcode(self):
        if self._MemIRCode : return self._MemIRCode
        else : return {'error' : 'Unknown status', 'code': '', 'encoder': ''}

    def readIRCodeFile(self):
        """lit le code sauvergarder d'un fichier type txt"""
        if not os.path.isfile(self._fileBackup) : 
            print("file {0} not exist, no code memorised at last".format(self._fileBackup))
            return False
        else :
            try:
                fich = open(self._fileBackup, "r")
            except :
                print 'error openning file : ', self._fileBackup
                return False
            else :
                if fich.readline() =="[LASTCODE]\n" :
                    code = {'error' :""}
                    code['code'], f = fich.readline().split("\n")
                    if fich.readline() == "[ENCODER]\n" :
                        code['encoder'], f = fich.readline().split("\n")
                        self._MemIRCode = code
                        retval = True
                        print "Code read from file : {0}".format(self._MemIRCode)
                    else: retval = False
                else: retval = False
                fich.close()
                return retval

    def writeIRCodeFile(self):
        """Ecrit le code sauvergarder d'un fichier type txt"""
        if self._MemIRCode :
            try:
                fich = open(self._fileBackup, "w")
            except :
                print 'error creating file : ', self._fileBackup
            else :
                fich.write("[LASTCODE]\n")
                fich.write("{0}\n".format(self._MemIRCode['code']))
                fich.write("[ENCODER]\n")
                fich.write("{0}\n".format(self._MemIRCode['encoder']))
                fich.close()
                print("Code Saved")
        else: print("no code to save.")

    def getState(self):
        """Renvoi le status du pin self.irAck qui corresponds à l'état de marche/arret."""
        if self.irAck:
            self.ackState = GPIO.input(self.irAck)
            print "GPIO {0} Input ACK, state : {1}\n".format(self.irAck, self.ackState)
            return {'error': "", 'state': self.ackState}
        else:
            print "No pin ack defined, can't get status."
            return {'error': "No pin ack defined, can't get status."}


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
                self.waitAck = time.time()
                codeIR = GPIO.BCMWatchPulsePairsGPIO(self.irReceiver)
                if codeIR : self.receiveRAWIRCode(codeIR)
                time.sleep(0.01)
            else : time.sleep(0.5)
    
    def callback_gpioEvent(self,  GPIOPin):
        if GPIOPin == self.irReceiver :
#            print"IR Receiver Event ..."
            self.waitAck = time.time()
            codeIR = GPIO.BCMWatchPulsePairsGPIO(self.irReceiver)
            if codeIR : self.receiveRAWIRCode(codeIR)
        else :
            print "IR Receiver Event on bad pin : {0}".format(GPIOPin)

    def callback_gpioAck(self,  GPIOPin):
        if GPIOPin == self.irAck :
            state = GPIO.input(GPIOPin)
            t = time.time()
            tdiff = t - self.tLastAck 
            print "********************* Callback: state {0}, time step {1} ************".format(state, tdiff)
            if self.ackState != state :
                if state and (tdiff > 0.01): 
                    if self.waitAck :
                        if t - self.waitAck < 0.4:
                            print"********* IR Receiver Ack on pin {0}, time : {1} *********\n".format(GPIOPin, tdiff)
                        else:
                            print"........ IR Receiver to long Ack on pin {0}, time : {1} ........\n".format(GPIOPin, tdiff)
                        self.waitAck = 0
                    else :
                        print"***** IR Receiver Ack on pin {0} without waiting ack, time : {1}\n".format(GPIOPin, tdiff)
                self.tLastAck = t
                self.ackState = state
            else : print"----- Ack Pin {0}, no change state : {1}".format(GPIOPin, state)
        else :
            print "***** IR Receiver Ack on bad pin : {0}\n".format(GPIOPin)


