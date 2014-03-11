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

DAIKINTIMINGS = {0: [440, 448], 1:[440,1288], 2: [3448, 1720], 3:[408, 29616]}
DAIKINHEADER = "210001000010110111110010000001111000000000000000000000000010000003"
DAIKINCODELENGHT = 145
DAIKINCKSLENGHT = 8

TOLERANCE = 150                # pulse/pause +-TOLERANCE range
LARGETOL = 2                     # Coefficient for large pulse/pause tolerance
NBOUTTOL = 10                   # Max number of pair in Large tolerance

class DaikinCodeException(Exception):
    """"Daikin code traduct exception class.
    """
    
    def __init__(self, value):
        """Initialisation"""
        Exception.__init__(self)
        self.msg = "Daikin code exception:"
        self.value = value
                                
    def __str__(self):
        """String format objet"""
        return repr(self.msg+' '+self.value)
        
class DaikinCode:
    
    STARTPULSE = [2,  10000]  #  Pulse Start bit [pulse, pause]
    ENDPULSE = [416,  40000]  #  Pulse Start bit [pulse, pause]
    
    def __init__(self,  timings = DAIKINTIMINGS,  tol =TOLERANCE,  lTol = LARGETOL,  maxOut = NBOUTTOL,  startP= True,  endP = False):
        self.timings = timings
        self.tol = tol
        self.lTol = tol * lTol
        self.maxOut = maxOut
        self.code =""
        self.startP = startP
        self.endP = endP
        
    def irCodeToRAW(self, code):
        pulsePairs = []
        try :
            for c in code :
                pulsePairs.append(self.timings[int(c)])
            if self.startP : pulsePairs.insert(0,  self.STARTPULSE)
            if self.endP : pulsePairs.append(self.ENDPULSE)
        except :
            DaikinCodeException("IR code bad format to Raw converting.")
        return pulsePairs

    def findTiming(self, pair,  outTol = False ):
        numT = []
        outT = False
        for t in self.timings :
            if (pair[0] >= self.timings[t][0] - self.tol) and (pair[0] <= self.timings[t][0] + self.tol) and (pair[1] >= self.timings[t][1] - self.tol) and (pair[1] <= self.timings[t][1] + self.tol) :
                numT.append(t)
        if  (len(numT) == 0) and (outTol) :
            for t in self.timings :
                if (pair[0] >= self.timings[t][0] - self.lTol) and (pair[0] <= self.timings[t][0] + self.lTol) and (pair[1] >= self.timings[t][1] - self.lTol) and (pair[1] <= self.timings[t][1] + self.lTol) :
                    numT.append(t)
                    outT = True
        if len(numT) == 1:
            return {"id": numT[0],  "largeTol" : outT}
        elif len(numT) == 0 :
            return {"id": -1, "largeTol" : outT}
        else :
            return {"id": -2, "largeTol" : outT}
        
    def validateChecksum(self,  code,  checksum):
        chk = 0
        for i  in range (1, len(code), 8):             # extraction par pas de 8 bits
            chk=chk + int (code[i:i+8][::-1], 2)    # addition des bytes après reverse bits
        checkV =  bin(chk)[::-1][0:8]                 # reconstruction de code checksum
        print checkV
        if checkV == checksum : return 1
        else : return 0

    def rawToIRCode(self,  pulsePairs):
        codeIR = ""
        error = ""
        largeTol = True
        outTol = 0
        if (pulsePairs[0][0] <= self.STARTPULSE[0] + self.tol) and (pulsePairs[0][1] >= self.STARTPULSE[1] - self.tol) :  # a long pulse for start bit detected
            print ("long pulse start bit detected")
            print pulsePairs.pop(0)
        for pair in pulsePairs:
            numT = self.findTiming(pair, largeTol)
            if numT["id"] >= 0 : 
                codeIR = codeIR + "{0}".format(numT["id"])
            else : codeIR = codeIR + "E"
            if numT["largeTol"] : 
                outTol += 1
                print ("pair in large tolerance")
                if outTol > self.maxOut :
                    print "Error, to much Large tolerance"
                    error = "Error, to much Large tolerance"
                    largeTol = False
        if codeIR :
            lenH = len(DAIKINHEADER)
            header = codeIR[:lenH]
            if header == DAIKINHEADER : 
                code = codeIR[lenH:lenH+DAIKINCODELENGHT]
                if code.find("E") >= 0 :  
                    error = "Code part error"
                else :
                    checksum = codeIR[lenH + DAIKINCODELENGHT: lenH + DAIKINCODELENGHT + DAIKINCKSLENGHT]
                    print checksum
                    if not self.validateChecksum(code,  checksum) :
                        error = "Invalide Checksum"
                    else :
                        codeIR = header + code + checksum
            else :  error = "Invalide Daikin header"
        print error
        print codeIR
        return {"code": codeIR,  "error": error}
            
        
