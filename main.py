import serial
import threading
import time
from pjnath import *
from pjmedia import *
from pjlib import *
from pj import *
import queue
import configparser

class SipParty:
    def __init__(self, name):
        self.name = name

    def send_data(self, data):
        print(f"{self.name} (SIP): Sending: {data}")

    def receive_data(self, data):
        print(f"{self.name} (SIP): Receiving: {data}")
        return data

class PJSUACallHandler(pjsua.CallCallback):
    def __init__(self):
        pjsua.CallCallback.__init__(self)

    def on_state(self, prm):
        pass

    def on_media_state(self, prm):
        pass

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
                self.sip_party.send_data(data_str)
                
                if data_str.startswith("AT"):
                    response = self.handle_at_command(data_str)
                    self.send_queue.put(response)
                else:
                    self.receive_queue.put(data_str)

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

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    com_config = config['VirtualModem']
    sip_config = {
        "username": config['SIP']['username'],
        "password": config['SIP']['password'],
        "server": config['SIP']['server']
    }

    sip_party = SipParty("Virtual Modem")
    virtual_modem = VirtualModem(com_config['com_port'], sip_config)
    virtual_modem.start()

    try:
        while True:
            if virtual_modem.running:
                received_data = virtual_modem.receive_queue.get()
                virtual_modem.send_queue.put(received_data)

            time.sleep(1)
    except KeyboardInterrupt:
        virtual_modem.stop()

if __name__ == "__main__":
    main()
