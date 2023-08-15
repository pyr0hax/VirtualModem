import serial
import time
import pjsua
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

com_port = config.get('Serial', 'com_port', fallback='COM1')
baud_rate = config.getint('Serial', 'baud_rate', fallback=9600)

sip_username = config.get('SIP', 'username', fallback='your_username')
sip_password = config.get('SIP', 'password', fallback='your_password')
asterisk_server_ip = config.get('SIP', 'server_ip', fallback='your_asterisk_server_ip')
sip_extension = config.get('SIP', 'extension', fallback='extension')

ser = serial.Serial(com_port, baud_rate, timeout=1)

def on_call_state(call):
    if call.info().state == pjsua.CallState.CONFIRMED:
        print("Call is confirmed")

pjsua.Lib.instance().init()
transport_config = pjsua.TransportConfig()
pjsua.Lib.instance().create_transport(pjsua.TransportType.UDP, transport_config)

account_config = pjsua.AccountConfig()
account_config.id = f"sip:{sip_username}@{asterisk_server_ip}"
account_config.reg_uri = f"sip:{asterisk_server_ip}"
account_config.cred_info = [pjsua.AuthCred("*", sip_username, sip_password)]

account = pjsua.Account()
account.create(account_config)

call = None

def perform_handshake():
    ser.write("ATZ\r".encode())
    response = ser.read_until("OK\r\n".encode(), timeout=5)
    
    if b'OK' in response:
        ser.setRTS(True)  
        time.sleep(1)     
        
        ser.setDTR(True)  
        time.sleep(1)     
        
        ser.write("CONNECT\r\n".encode())
        print("Handshake successful. Modems connected.")
        return True
    else:
        print("Handshake failed.")
        return False

try:
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode().strip()
            print(f"Received from Serial: {data}")
            
            if data.startswith("AT"):
                if data == "ATD":
                    call = account.make_call(f"sip:{sip_extension}@{asterisk_server_ip}", cb=on_call_state)
                elif data == "ATH":
                    if call:
                        call.hangup()
                        call = None
                else:
                    pass
            else:
                if call:
                    try:
                        call.send_dtmf(data)
                    except pjsua.Error as e:
                        print(f"Error sending DTMF: {e}")
        
        events = pjsua.Lib.instance().handle_events()
        for event in events:
            if event.type == pjsua.PJSIP_EVENT_CALL_MEDIA_STATE:
                if call and call.info().media_state == pjsua.MediaState.ACTIVE:
                    while call.info().media_state == pjsua.MediaState.ACTIVE:
                        try:
                            dtmf = call.get_dtmf()
                            if dtmf:
                                print(f"Received from SIP: {dtmf}")
                                ser.write(dtmf.encode())
                        except pjsua.Error as e:
                            break
                        
                    if ser.in_waiting > 0:
                        data = ser.readline().decode().strip()
                        if data:
                            print(f"Received from remote modem: {data}")
                            
                            if call:
                                try:
                                    call.send_dtmf(data)
                                except pjsua.Error as e:
                                    print(f"Error sending data over SIP: {e}")
                
except KeyboardInterrupt:
    pass
finally:
    if call:
        call.hangup()
    pjsua.Lib.instance().shutdown()
    ser.close()
