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
import sys
import os
import time

JSON Message structure, keys :
    - 'header' : according to wsserver specifications : 'header' :{{'type',  'idws', 'idmsg', 'ip', 'timestamp' }} see wsserver.py
    - header type = 'req-ack' : Client request with ack
        - 'resquest' : Client resquest a WebSocket server action.
            - 'server-hbeat' : recept an hbeat
                    Value set : nothing
                    Value ack returned : 
                        {"error" : "", "request": "server-hbeat",
                          "data" : {"error" : ""}}
            - 'sendIRCode' : sending an IR code through RpiIRTrans
                    Value set : 
                        {"datatype": "", "code": "", "encoder": ""}
                    Value ack returned :                   
                        {"error": "if, Global message", "request": "sendircode",
                          "data": {"encoder": "", "code": "", "error": "if, encoder message" or ""}}
            - 'getMemircode' : return (by ack) the last (current) code in memory.
                    Value set : nothing
                    Value ack returned :
                        {"error": "if, Global message", "request": "getMemIRCode",
                          "data": {"encoder": "", "code": "", "error": "if, encoder message" or ""}}
            - 'setTolerances'
                    Value set : 
                        {"tolerances": {<A dict Function of encoder, DAIKIN example> "large": 300, "maxout": 10, "tolerance": 150}, "encoder": ""}
                    Value ack returned :
                        {"error": "if, Global message", "request": "setTolerances", 
                          "data": {"error": "if, bad parameters" or ""}}
            - 'getTolerances'
                    Value set : {"encoder": "" }
                    Value ack returned :
                        {"error": ""if, Global message", "request": "getTolerances", 
                          "data": {"tolerances": {<A dict Function of encoder, DAIKIN example> "large": 300, "maxout": 10, "tolerance": 150}, "encoder" : "", "error": "if, encoder message" or ""}}
            - 'getState'
                    Value set : nothing
                    Value ack returned :
                        {"error": "" message if no pin set for state capability.", 
                          "data": {"state": 0 or 1 for on/ off status, 0 if no capability, "error": "message if no pin set for state capability." or ""}}
                      
    - header type = 'pub' : Message broadcast for all client
        - "host": "<Name of server host>",
        - "type" : The type of plushed message
            - 'codereceived' : an ir code if received by IRTrans.
                - "data": {"encoder": "", "code": ""', "error": "if, encoder message" or ""}}
            - 'hardState' : if capability and codereceived is not reconized publish hard state.
                - "data": {"state": 0 or 1, "error":""}
            

 'datatype' : Encoding type of data ("RAW", "BinTimings", "HEX")
 'encoder' : Encoder protocole ("DAIKIN", "RC5", ...)
 'code', 'code' : Infrared code
 'tolerances': A dict depending of encoder, type for example DAIKIN : {"tolerance": 150, "large": 300, "maxout": 10}
 'error' :  for ack message, report an error text or "" if not.
 
- Client sender example message :
    {
        "header":
            {
                "idws": 42865, 
                "idmsg": 48650, 
                "type": "req-ack", 
                "timestamp": 1394795765.299422, 
                "ip": "192.168.0.1"
            },
        "request": "sendIRCode", 
        "datatype": "BinTimings", 
        "code": "2100010...............0010000110", 
        "encoder": "DAIKIN"
    }

- Sended ack response :
    {
        "header": 
            {
                "idws": 42865, 
                "idmsg": 48650, 
                "type": "ack", 
                "timestamp": 139479691970, 
                "ip": "192.168.0.2"
            }, 
        "request": "sendIRCode", 
        "error": "", 
        "data": 
            {
                "encoder": "DAIKIN", 
                "code": "2100010...............0010000110", 
                "error": "No encoder finded"
            }
        }
    }

- Sended pub response :
       "header": 
            {
                "idws": 42865, 
                "idmsg": 48650, 
                "type": "pub", 
                "timestamp": 139479691970, 
                "ip": "192.168.0.2"
            }, 
        "type" : "codereceived",
        "data": 
            {
                "encoder": "DAIKIN", 
                "code": "2100010...............0010000110"', 
                "error": ""
            }
        }
    }

"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.rpi_irtrans import RpiIRTrans
from lib.daikincode import DaikinCode
from lib.wsserver import BroadcastServer

class RpiTransceiverException(Exception):
    """Rpi Transceiver generic exception class.
    """
    def __init__(self, value):
        """Initialisation"""
        Exception.__init__(self)
        self.msg = "Rpi Transceiver generic exception:"
        self.value = value
                                
    def __str__(self):
        """String format objet"""
        return repr(self.msg+' '+self.value)

class RpiTransceiver():
    
    def __init__(self,  wsPort):
        self._irTrans = RpiIRTrans(self, 18, 25, 17, 38000)
        self._irTrans.register_Encoder("DAIKIN",  DaikinCode())
        self._log = None
        self._wsServer =  BroadcastServer(wsPort,  self.cb_ServerWS,  self._log) # demarre le websocket server
        self._run()
    
    def cb_ServerWS(self, message):
        """Callback en provenance d'un client via server Websocket (resquest avec ou sans ack)"""
        blockAck = False
        report = {'error':  'Message not handle.'}
        ackMsg = {}
        erAck = ''
        self._irTrans.getState()
        print "WS - Client Request",  message
        if message.has_key('header') :
            if message['header']['type'] in ('req', 'req-ack'):
                if message['request'] == 'server-hbeat' :
                    report['error'] =''
                elif message['request'] == 'sendIRCode' :
                    erAck = "IR emitter don't confirm final reception."
                    report = self._irTrans.sendIRCode(message['encoder'],  message['datatype'], message['code'])
                elif message['request'] == 'getMemIRCode' :
                    erAck = 'Fail to get IR Code in memory.'
                    report = self._irTrans.getMemIRcode()
                elif message['request'] == 'setTolerances' :
                    erAck = 'Fail to set tolerances.'
                    report = self._irTrans.setTolerances(message['encoder'],  message['tolerances'])
                elif message['request'] == 'getTolerances' :
                    erAck = 'Fail to get tolerances.'
                    report = self._irTrans.getTolerances(message['encoder'])
                elif message['request'] == 'getState' :
                    erAck = 'Fail to get state.'
                    report = self._irTrans.getState()
                else :
                    erAck = 'Client request Fail.'
                    report['error'] ='Unknown request.'
                    print "commande inconnue"
            if message['header']['type'] == 'req-ack' and not blockAck :
                ackMsg['header'] = {'type': 'ack',  'idws' : message['header']['idws'], 'idmsg' : message['header']['idmsg'],
                                               'ip' : message['header']['ip'] , 'timestamp' : long(time.time()*100)}
                ackMsg['request'] = message['request']
                if report :
                    if report['error'] != '':
                        ackMsg['error'] = erAck
                    else :
                        ackMsg['error'] = ''
                    ackMsg['data'] = report
                else : 
                    ackMsg['error'] = 'No data report.'
                self._wsServer.sendAck(ackMsg)
        else :
            raise RpiTransceiverException("WS request bad format : {0}".format(message))
        
    def _run(self):
        print "Manager Started"
        try:
            while 1 :
                time.sleep(1)
        finally:  # when you CTRL+C exit, we clean up 
            self._irTrans.close()
            self._wsServer.close()
            print" *** Clean up exit :)"
   
    def sendToWSClients(self, type,  message):
        msg = {"host" : os.uname()[1], 'type': type,  'data': message}
        print "message to clients : {0}".format(msg)
        if  self._wsServer : self._wsServer.broadcastMessage(msg)

def main():
    RpiTransceiver(5590)
    print" *** Clean up exit :)"    
    
if __name__ == "__main__":
    RpiTransceiver(5590)
    print" *** Clean up exit :)"
