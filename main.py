import time
import configparser
from virtualmodem import VirtualModem

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')

    com_config = config['VirtualModem']
    sip_config = {
        "username": config['SIP']['username'],
        "password": config['SIP']['password'],
        "server": config['SIP']['server']
    }

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
