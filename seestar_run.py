import socket
import json
import time
from datetime import datetime
import threading
import sys

class SeestarClient:
    def __init__(self, ip, port, cmdid):
        self.ip = ip
        self.port = port
        self.cmdid = cmdid

    # Auto-increment the command ID each time we use it
    def get_cmdid(self):
        cmdid = self.cmdid
        self.cmdid += 1
        return cmdid

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.ip, self.port))
        self.socket = s
        return s

    def reconnect(self):
        return self.connect()

    def get_socket_msg(self):
        try:
            data = self.socket.recv(1024 * 60)  # comet data is >50kb
        except socket.error as e:
            self.reconnect()
            data = self.socket.recv(1024 * 60)
        data = data.decode("utf-8")
        if is_debug:
            print("Received :", data)
        return data

    def send_message(self, data):
        try:
            self.socket.sendall(data.encode())  # TODO: would utf-8 or unicode_escaped help here
        except socket.error as e:
            self.reconnect()
            self.send_message(data)

    def json_message(self, instruction):
        data = {"id": self.get_cmdid(), "method": instruction}
        json_data = json.dumps(data)
        if is_debug:
            print("Sending %s" % json_data)
        self.send_message(json_data+"\r\n")

    def json_message2(self, data):
        if data:
            json_data = json.dumps(data)
            if is_debug:
                print("Sending2 %s" % json_data)
            resp = self.send_message(json_data + "\r\n")

    def set_op_state(self, state):
        self.op_state = state

    def get_op_state(self):
        return self.op_state

    #I noticed a lot of pairs of test_connection followed by a get if nothing was going on
    def heartbeat(self):
        self.json_message("test_connection")

    def send_command(self, command, params):
        data = {
            'id': self.get_cmdid(),
            'method': command,
            'params': params,
        }
        self.json_message2(data)


    def goto_target(self, ra, dec, target_name, is_lp_filter):
        print("going to target...")
        params = {
            'mode': 'star',
            'target_ra_dec': [ra, dec],
            'target_name': target_name,
            'lp_filter': is_lp_filter,
        }
        self.send_command('iscope_start_view', params)

    def start_stack(self):
        print("starting to stack...")
        params = { 'restart': True }
        self.send_command('iscope_start_stack', params)

    def stop_stack():
        print("stop stacking...")
        params = { 'stage': 'Stack' }
        self.send_command('iscope_stop_view', params)


def receieve_message_thread_fn():
    global is_watch_events
    global client
        
    msg_remainder = ""
    while is_watch_events:
        #print("checking for msg")
        data = client.get_socket_msg()
        if data:
            msg_remainder += data
            first_index = msg_remainder.find("\r\n")
            
            while first_index >= 0:
                first_msg = msg_remainder[0:first_index]
                msg_remainder = msg_remainder[first_index+2:]            
                parsed_data = json.loads(first_msg)
                
                if 'Event' in parsed_data and parsed_data['Event'] == "AutoGoto":
                    state = parsed_data['state']
                    print("AutoGoto state: %s" % state)
                    if state == "complete" or state == "fail":
                        client.set_op_state(state)
                
                if is_debug:
                    print(parsed_data)
                    
                first_index = msg_remainder.find("\r\n")
        time.sleep(1)



def wait_end_op():
    global client
    client.set_op_state("working")
    heartbeat_timer = 0
    while client.get_op_state() == "working":
        heartbeat_timer += 1
        if heartbeat_timer > 5:
            heartbeat_timer = 0
            client.heartbeat()
        time.sleep(1)

    
def sleep_with_heartbeat():
    global client
    stacking_timer = 0
    while stacking_timer < session_time:         # stacking time per segment
        stacking_timer += 1
        if stacking_timer % 5 == 0:
            client.heartbeat()
        time.sleep(1)

def parse_ra_to_float(ra_string):
    # Split the RA string into hours, minutes, and seconds
    hours, minutes, seconds = map(float, ra_string.split(':'))

    # Convert to decimal degrees
    ra_decimal = hours + minutes / 60 + seconds / 3600

    return ra_decimal
    
def parse_dec_to_float(dec_string):
    # Split the Dec string into degrees, minutes, and seconds
    if dec_string[0] == '-':
        sign = -1
        dec_string = dec_string[1:]
    else:
        sign = 1
    print(dec_string)
    degrees, minutes, seconds = map(float, dec_string.split(':'))

    # Convert to decimal degrees
    dec_decimal = sign * (degrees + minutes / 60 + seconds / 3600)

    return dec_decimal
    
is_watch_events = True
    
def main():
    global HOST
    global PORT
    global session_time
    global is_watch_events
    global is_debug
    global client
    
    version_string = "1.0.0b1"
    print("seestar_run version: ", version_string)
    
    if len(sys.argv) != 11 and len(sys.argv) != 12:
        print("expected seestar_run <ip_address> <target_name> <ra> <dec> <is_use_LP_filter> <session_time> <RA panel size> <Dec panel size> <RA offset factor> <Dec offset factor>")
        sys.exit()
    
    HOST= sys.argv[1]
    target_name = sys.argv[2]
    try:
        center_RA = float(sys.argv[3])
    except ValueError:
        center_RA = parse_ra_to_float(sys.argv[3])
        
    try:
        center_Dec = float(sys.argv[4])
    except ValueError:
        center_Dec = parse_dec_to_float(sys.argv[4])
    
    is_use_LP_filter = sys.argv[5] == '1'
    session_time = int(sys.argv[6])
    nRA = int(sys.argv[7])
    nDec = int(sys.argv[8])
    mRA = float(sys.argv[9])
    mDec = float(sys.argv[10])
    is_debug = False

    if len(sys.argv) == 12:
        is_debug = sys.argv[11]=="Kai"
        
    print(HOST, target_name, center_RA, center_Dec, is_use_LP_filter, session_time, nRA, nDec, mRA, mDec)
    
    # verify mosaic pattern
    if nRA < 1 or nDec < 0:
        print("Mosaic size is invalid")
        sys.exit()
    
    print("nRA: %d", nRA)
    print("nDec:%d", nDec)
    
    PORT = 4700 
    cmdid = 999

    client = SeestarClient(HOST, PORT, cmdid)

    delta_RA = 0.06
    delta_Dec = 0.9

    s = client.connect()
    with s:
        
        # flush the socket input stream for garbage
        #get_socket_msg()
        
        if center_RA < 0:
            client.json_message("scope_get_equ_coord")
            data = get_socket_msg()
            parsed_data = json.loads(data)
            if parsed_data['method'] == "scope_get_equ_coord":
                data_result = parsed_data['result']
                center_RA = float(data_result['ra'])
                center_Dec = float(data_result['dec'])
                print(center_RA, center_Dec)
            
        # print input requests
        print("received parameters:")
        print("  ip address    : " + client.ip)
        print("  target        : " + target_name)
        print("  RA            : ", center_RA)
        print("  Dec           : ", center_Dec)
        print("  use LP filter : ", is_use_LP_filter)
        print("  session time  : ", session_time)
        print("  RA num panels : ", nRA)
        print("  Dec num panels: ", nDec)
        print("  RA offset x   : ", mRA)
        print("  Dec offset x  : ", mDec)
        
        delta_RA *= mRA
        delta_Dec *= mDec
        
        # adjust mosaic center if num panels is even
        if nRA % 2 == 0:
            center_RA += delta_RA/2
        if nDec % 2 == 0:
            center_Dec += delta_Dec/2
        
        get_msg_thread = threading.Thread(target=receieve_message_thread_fn)
        get_msg_thread.start()
        
        mosaic_index = 0
        cur_ra = center_RA-int(nRA/2)*delta_RA
        for index_ra in range(nRA):
            cur_dec = center_Dec-int(nDec/2)*delta_Dec
            for index_dec in range(nDec):
                if nRA == 1 and nDec == 1:
                    save_target_name = target_name
                else:
                    save_target_name = target_name+"_"+str(index_ra+1)+str(index_dec+1)
                print("goto ", (cur_ra, cur_dec))
                client.goto_target(cur_ra, cur_dec, save_target_name, is_use_LP_filter)
                wait_end_op()
                print("Goto operation finished")
                
                time.sleep(3)
                
                if client.get_op_state() == "complete":
                    client.start_stack()
                    sleep_with_heartbeat()
                    client.stop_stack()
                    print("Stacking operation finished" + save_target_name)
                else:
                    print("Goto failed.")
                    
                cur_dec += delta_Dec
                mosaic_index += 1
            cur_ra += delta_RA
        
        
    print("Finished seestar_run")
    is_watch_events = False
    get_msg_thread.join(timeout=5)
    sys.exit()
    
    
    

# seestar_run <ip_address> <target_name> <ra> <dec> <is_use_LP_filter> <session_time> <RA panel size> <Dec panel size> <RA offset factor> <Dec offset factor>
# python seestar_run.py 192.168.110.30 'Castor' '7:24:32.5' '-41:24:23.5' 0 60 2 2 1.0 1.0
# python seestar_run.py 192.168.110.30 'Castor' '7:24:32.5' '+41:24:23.5' 0 60 2 2 1.0 1.0
# python seestar_run.py 192.168.110.30 'Castor' '7:24:32.5' '41:24:23.5' 0 60 2 2 1.0 1.0
# python seestar_run.py 192.168.110.30 'Castor' 7.4090278 41.4065278 0 60 2 2 1.0 1.0
if __name__ == "__main__":
    main()
    

 
