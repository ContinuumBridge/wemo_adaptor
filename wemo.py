#!/usr/bin/env python
# wemoadaptor.py
# Copyright (C) ContinuumBridge Limited, 2013-2014 - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Peter Claydon
#
ModuleName = "WeMo"
WEMO = "/usr/local/bin/wemo"

import sys
import time
import os
import logging
import subprocess
from cbcommslib import CbAdaptor
from cbconfig import *
from twisted.internet import threads
from twisted.internet import reactor
from ouimeaux.environment import Environment

class Adaptor(CbAdaptor):
    def __init__(self, argv):
        logging.basicConfig(filename=CB_LOGFILE,level=CB_LOGGING_LEVEL,format='%(asctime)s %(message)s')
        self.state = "idle"
        self.previousState = "off"
        self.apps = []
        #CbAdaprot.__init__ MUST be called
        CbAdaptor.__init__(self, argv)

    def setState(self, action):
        if self.state == "idle":
            if action == "connected":
                self.state = "connected"
            elif action == "inUse":
                self.state = "inUse"
        elif self.state == "connected":
            if action == "inUse":
                self.state = "activate"
        elif self.state == "inUse":
            if action == "connected":
                self.state = "activate"
        if self.state == "activate":
            if not self.apps:
                # No apps are using this switch
                logging.info("%s %s No apps using switch", ModuleName, self.id)
            elif self.sim == 0:
                logging.debug("%s %s Activated", ModuleName, self.id)
            self.state = "running"
        logging.debug("%s %s state = %s", ModuleName, self.id, self.state)

    def reportState(self, state):
        logging.debug("%s %s Switch state = %s", ModuleName, self.id, state)
        msg = {"id": self.id,
               "timeStamp": time.time(),
               "content": "switch_state",
               "data": state}
        for a in self.apps:
            self.sendMessage(msg, a)

    def onAppInit(self, message):
        logging.debug("%s %s %s onAppInit, req = %s", ModuleName, self.id, self.friendly_name, message)
        resp = {"name": self.name,
                "id": self.id,
                "status": "ok",
                "functions": [{"parameter": "switch",
                               "type": "240V",
                               "purpose": "heater"}],
                "content": "functions"}
        self.sendMessage(resp, message["id"])

    def onAppRequest(self, message):
        logging.debug("%s %s %s onAppRequest, message = %s", ModuleName, self.id, self.friendly_name, message)
        # Switch off anything that already exists for this app
        if req["id"] not in self.apps:
            if "switch" in req["functions"]:
                self.apps.append(req["id"])  
        else:
            if "switch" not in req["functions"]:
                self.apps.remove(req["id"])  
        self.checkAllProcessed(message["id"])

    def onOff(self, numState):
        if numState == "1":
            return "on"
        else:
            return "off"

    def onAppCommand(self, message):
        if self.configured:
            state = self.previousState
            # If at first it doesn't succeed, try again.
            for i in range(2):
                if message["data"] == "on" and self.previousState == "off":
                    output = subprocess.check_output([WEMO, "switch", self.switchName, "on"])
                    output = subprocess.check_output([WEMO, "switch", self.switchName, "status"])
                    output = output[:-1]
                    state = self.onOff(output)
                    if state == "on":
                        break
                elif message["data"] == "off" and self.previousState == "on":
                    output = subprocess.check_output([WEMO, "switch", self.switchName, "off"])
                    output = subprocess.check_output([WEMO, "switch", self.switchName, "status"])
                    output = output[:-1]
                    state = self.onOff(output)
                    if state == "off":
                        break
            if state != self.previousState:
                self.reportState(state)
                self.previousState = state
        else:
            logging.debug("%s %s %s onAppCommand before init complete", ModuleName, self.id, self.friendly_name)

    def onConfigureMessage(self, config):
        if not self.configured:
            logging.info("%s %s %s Init", ModuleName, self.id, self.friendly_name)
            output = subprocess.check_output([WEMO, "list"])
            self.switchName = output.split(' ')[1]
            if self.switchName.endswith('\n'):
                self.switchName = self.switchName[:-1]
            output = subprocess.check_output([WEMO, "switch", self.switchName, "status"])
            output = output[:-1]
            switchState = self.onOff(output)
            logging.info("%s %s %s Switch state on init: %s", ModuleName, self.id, self.friendly_name, switchState)
            self.previousState = switchState
            self.configured = True

if __name__ == '__main__':
    adaptor = Adaptor(sys.argv)

