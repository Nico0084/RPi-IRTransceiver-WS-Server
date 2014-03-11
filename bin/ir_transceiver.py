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
    - 'header' : according to wsserver specifications : {'type',  'idws', 'idmsg', 'ip', 'timestamp' } see wsserver.py
    - 'resquest' : Client resquest a WebSocket server action.
        - 'sendIRCode' : sending an IR code through RpiIRTrans
        - 'getCurrentCode' : return (by ack) the last (current) code in memory.
    - 'DataType' : Encoding type of data ("RAW", "BinTimings", "HEX")
    - 'Encoder' : Encoder protocole ("DAIKIN", "RC5", ...)
    - 'IRCode' : code ir
    - 'error' :  for ack message, report an error text or "" if not.
Ack msg use same structure
pub Message
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
        self._irTrans = RpiIRTrans(self,  18, 25, 38000)
        self._irTrans.register_Coder("DAIKIN",  DaikinCode())
        self._log = None
        self._wsServer =  BroadcastServer(wsPort,  self.cb_ServerWS,  self._log) # demarre le websocket server
        self._run()
    
    def cb_ServerWS(self, message):
        """Callback en provenance d'un client via server Websocket (resquest avec ou sans ack)"""
        blockAck = False
        report = {'error':  'Message not handle.'}
        ackMsg = {}
        print "WS - Client Request",  message
        if message.has_key('header') :
            if message['header']['type'] in ('req', 'req-ack'):
                if message['request'] == 'sendIRCode' :
                    report = self._irTrans.sendIRCode(message['Encoder'],  message['DataType'], message['IRCode'])
                else :
                    report['error'] ='Unknown request.'
                    print "commande inconnue"
            if message['header']['type'] == 'req-ack' and not blockAck :
                ackMsg['header'] = {'type': 'ack',  'idws' : message['header']['idws'], 'idmsg' : message['header']['idmsg'],
                                               'ip' : message['header']['ip'] , 'timestamp' : long(time.time()*100)}
                ackMsg['request'] = message['request']
                if report :
                    if 'error' in report :
                        ackMsg['error'] = report['error']
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
   
    def sendToWSClients(self, message):
        msg = {"host" : "RPI_PAC_Salon"}
        msg.update(message)
        print "message to clients : {0}".format(msg)
        if  self._wsServer : self._wsServer.broadcastMessage(msg)
            
if __name__ == "__main__":
    RpiTransceiver(5590)
    print" *** Clean up exit :)"
