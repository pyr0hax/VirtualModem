import serial
import threading
import queue
from pjnath import *
from pjmedia import *
from pjlib import *
from pj import *
from pjsuacallback import PJSUACallHandler

class VirtualModem:
    def __init__(self, com_port, sip_config):
        self.com_port = com_port
        self.sip_config = sip_config
        self.serial = None
        self.running = False
        self.pjsua = None
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()

    def initialize(self):
        pjsua_lib.init()
        self.pjsua = pjsua.Lib()
        self.pjsua.init()

        acc_config = pjsua.AccountConfig()
        acc_config.id = 'sip:' + self.sip_config['username'] + '@' + self.sip_config['server']
        acc_config.reg_uri = 'sip:' + self.sip_config['server']
        self.account = self.pjsua.create_account(acc_config)

        self.serial = serial.Serial(self.com_port, baudrate=9600)

    def handle_incoming_data(self):
        while self.running:
            if self.serial.in_waiting > 0:
                data = self.serial.read(self.serial.in_waiting)
                data_str = data.decode('utf-8')

                if data_str.startswith("AT"):
                    response = self.handle_at_command(data_str)
                    self.send_queue.put(response)
                else:
                    self.receive_queue.put(data_str)

                if self.call and self.call.info().state == pjsua.CallState.CONFIRMED:
                    self.call.info().media_state = pjsua.MediaState.ACTIVE

    def handle_outgoing_data(self):
        while self.running:
            try:
                data = self.send_queue.get(timeout=0.1)
                self.serial.write(data.encode('utf-8'))
            except queue.Empty:
                pass

    def handle_at_command(self, at_command):
        if at_command == "AT":
            response = "OK"
        elif at_command == "ATI":
            response = "Virtual Modem Version 1.0"
        elif at_command.startswith("ATD"):
            response = "Dialing..."
            callee_uri = at_command.split("ATD", 1)[1]
            self.make_call(callee_uri)
        elif at_command == "ATA":
            response = "Answering call..."
        elif at_command == "ATH":
            response = "Hanging up..."
        elif at_command == "ATZ":
            response = "Modem reset"
        elif at_command == "AT+CMGS":
            response = "Enter SMS text"
        elif at_command == "AT+CMGR":
            response = "SMS message content"
        elif at_command == "AT+CREG":
            response = "+CREG: 0,1"
        elif at_command == "AT+CSQ":
            response = "+CSQ: 20,0"
        else:
            response = "ERROR"
        return response

    def make_call(self, callee_uri):
        call_setting = pjsua.CallSetting()
        call_setting.aud_cnt = 1
        call_setting.vid_cnt = 0

        self.call = self.account.make_call(callee_uri, call_setting)
        self.call_cb = PJSUACallHandler()
        self.call.set_callback(self.call_cb)

    def start(self):
        self.initialize()
        self.running = True

        incoming_thread = threading.Thread(target=self.handle_incoming_data)
        outgoing_thread = threading.Thread(target=self.handle_outgoing_data)

        incoming_thread.start()
        outgoing_thread.start()

    def stop(self):
        self.running = False
        self.serial.close()
        self.pjsua.destroy()
        self.pjsua.libDestroy()
