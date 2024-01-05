from dataclasses import dataclass
from configparser import ConfigParser

import gpiod
import time
import os



SYNC = 0b1010
RESERVED = 0b1001 # This is a DNC but is included in the CRC

BAUD = (1/9600)

@dataclass
class TrinamicRegister:
    """Address: Where in memory the registers are located\n
     Value: The value read/written from/to the register\n
     Access: What type of access the register has. Key below.\n
     Mask: ANDing the bits with the mask will leave the appropriate bits to write\n
     Access: R = Read ; W = Write ; RW = Read Write ; RC = Read Clear (write a 1 to clear)
     """
    address: int
    value: int
    access: str
    mask: int
    


class TMC5240:
    def __init__(self, addr, config_file = None):
        self.addr = addr

        # General Config Registers
        self.gconf = TrinamicRegister(0x00, 0x0000_0000, 'RW', 0x001F_F196) 
        self.gstat = TrinamicRegister(0x01, 0x0000_0000, 'RC', 0x0000_001F)   
        self.ifcnt = TrinamicRegister(0x02, 0x0000_0000, 'R', 0x0000_00FF)
        self.nodeconf = TrinamicRegister(0x03, 0x0000_0000, 'RW', 0x0000_0FFF) 
        self.io = [
            # Bit 0x0C is Read/Write
            # Others are Read only
            TrinamicRegister(0x04, 0x0000_0000, 'R', 0xFF07_EFFF),
            TrinamicRegister(0x04, 0x0000_0000, 'RW', 0x0000_1000)  
        ]
        self.x_comp = [ 
            TrinamicRegister(0x05, 0x0000_0000, 'RW', 0xFFFF_FFFF),   
            TrinamicRegister(0x06, 0x0000_0000, 'RW', 0x00FF_FFFF)   
        ]
        self.drv_conf = TrinamicRegister(0x0A, 0x0000_0000, 'RW', 0x0000_0033) 
        self.global_scalar = TrinamicRegister(0x0B, 0x0000_0000, 'RW', 0x0000_00FF)  

        # Velocity Dependent Config Registers
        self.i_hold_i_run = TrinamicRegister(0x10, 0x0000_0000, 'RW', 0x0F0F_1F1F)
        self.t_pwr_down = TrinamicRegister(0x11, 0x0000_0000, 'RW', 0x0000_00FF)
        self.t_step = TrinamicRegister(0x12, 0x0000_0000, 'R', 0x000F_FFFF)
        self.t_pwm_t_hrs = TrinamicRegister(0x13, 0x0000_0000, 'RW', 0x000F_FFFF)
        self.t_cool_t_hrs = TrinamicRegister(0x14, 0x0000_0000, 'RW', 0x000F_FFFF)
        self.t_high = TrinamicRegister(0x15, 0x0000_0000, 'RW', 0x000F_FFFF)

        # Ramp Generator Registers
        self.ramp_mode = TrinamicRegister(0x20, 0x0000_0000, 'RW', 0x0000_0003)
        self.x_act = TrinamicRegister(0x21, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.v_act = TrinamicRegister(0x22, 0x0000_0000, 'R', 0x00FF_FFFF)
        self.v_start = TrinamicRegister(0x23, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.a1 = TrinamicRegister(0x24, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.v1 = TrinamicRegister(0x25, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.a_max = TrinamicRegister(0x26, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.v_max = TrinamicRegister(0x27, 0x0000_0000, 'RW', 0x007F_FFFF)
        self.d_max = TrinamicRegister(0x28, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.tv_max = TrinamicRegister(0x29, 0x0000_0000, 'RW', 0x0000_FFFF)
        self.d1 = TrinamicRegister(0x2A, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.v_stop = TrinamicRegister(0x2B, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.t_zero_wait = TrinamicRegister(0x2C, 0x0000_0000, 'RW', 0x0000_FFFF)
        self.x_target = TrinamicRegister(0x2D, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.v2 = TrinamicRegister(0x2E, 0x0000_0000, 'RW', 0x000F_FFFF)
        self.a2 = TrinamicRegister(0x2F, 0x0000_0000, 'RW', 0x0003_FFFF)
        self.d2 = TrinamicRegister(0x30, 0x0000_0000, 'RW', 0x0003_FFFF)


        # Ramp Generator Driver Feature Control Registers
        self.vdc_min = TrinamicRegister(0x33, 0x0000_0000, 'RW', 0x007F_FFFF)
        self.sw_mode = TrinamicRegister(0x34, 0x0000_0000, 'RW', 0x0000_7FFF)
        self.ramp_stat = [
            TrinamicRegister(0x35, 0x0000_0000, 'R', 0x0000_EF33),
            TrinamicRegister(0x35, 0x0000_0000, 'RC', 0x0000_10CC)
        ]
        self.x_latch = TrinamicRegister(0x36, 0x0000_0000, 'R', 0xFFFF_FFFF)

        # Encoder Registers
        self.enc_mode = TrinamicRegister(0x38, 0x0000_0000, 'RW', 0x0000_07FF)
        self.x_enc = TrinamicRegister(0x39, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.enc_const = TrinamicRegister(0x3A, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.enc_stat = TrinamicRegister(0x3B, 0x0000_0000, 'RC', 0x0000_0003)
        self.enc_latch = TrinamicRegister(0x3C, 0x0000_0000, 'R', 0xFFFF_FFFF)
        self.enc_dev = TrinamicRegister(0x3D, 0x0000_0000, 'RW', 0x000F_FFFF)
        self.virt_stop_l = TrinamicRegister(0x3E, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.virt_stop_r = TrinamicRegister(0x3F, 0x0000_0000, 'RW', 0xFFFF_FFFF)

        # ADC Registers
        self.adc_vsup_ain = TrinamicRegister(0x50, 0x0000_0000, 'R', 0x1FFF_1FFF)
        self.adc_temp = TrinamicRegister(0x51, 0x0000_0000, 'R', 0x1FFF_1FFF)
        self.otw_ov_vth = TrinamicRegister(0x52, 0x0000_0000, 'RW', 0x1FFF_1FFF)

        # Motor Drive Registers
        self.mslut_0 = TrinamicRegister(0x60, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_1 = TrinamicRegister(0x61, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_2 = TrinamicRegister(0x62, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_3 = TrinamicRegister(0x63, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_4 = TrinamicRegister(0x64, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_5 = TrinamicRegister(0x65, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_6 = TrinamicRegister(0x66, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_7 = TrinamicRegister(0x67, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_sel = TrinamicRegister(0x68, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.mslut_start = TrinamicRegister(0x69, 0x0000_0000, 'RW', 0xFFFF_00FF)
        self.mscnt = TrinamicRegister(0x6A, 0x0000_0000, 'R', 0x0000_03FF)
        self.mscuract = TrinamicRegister(0x6B, 0x0000_0000, 'R', 0x01FF_01FF)
        self.chop_conf = TrinamicRegister(0x6C, 0x0000_0000, 'RW', 0xFFFD_DFFF)
        self.cool_conf = TrinamicRegister(0x6D, 0x0000_0000, 'RW', 0x017F_EF6F)
        self.dc_ctrl = TrinamicRegister(0x6E, 0x0000_0000, 'RW', 0x00FF_03FF)
        self.drv_status = TrinamicRegister(0x6F, 0x0000_0000, 'R', 0xFF1F_F3FF)
        self.pwm_conf = TrinamicRegister(0x70, 0x0000_0000, 'RW', 0xFFFF_FFFF)
        self.pwm_scale = TrinamicRegister(0x71, 0x0000_0000, 'R', 0x01FF_03FF)
        self.pwm_auto = TrinamicRegister(0x72, 0x0000_0000, 'R', 0x00FF_00FF)
        self.sg4_thrs = TrinamicRegister(0x74, 0x0000_0000, 'RW', 0x0000_03FF)
        self.sg4_result = TrinamicRegister(0x75, 0x0000_0000, 'R', 0x0000_03FF)
        self.sg4_ind = TrinamicRegister(0x76, 0x0000_0000, 'R', 0xFFFF_FFFF)
        
        if config_file is None:
            pass
        else:
            self.load_config(config_file)

    def get_address():
        return self.addr

    def get_gconf(self, line, debug=False):
        payload = generate_read_payload(self, self.gconf.address)
        print(f"Payload: {hex(payload)}")
        if(debug):
            pause("Payload Generated")
        write_payload(line, payload, 32)
        if(debug): pause("Payload Written")
        reply = read_reply(line)
        if(debug): pause("Reply Read")
        print(f"Data Read: {hex(reply)}")
        return
    
    def set_gconf(self, line, value, debug=False):
        payload = generate_write_payload(self, self.gconf.address, value)
        if(debug): 
            print(f"Payload: {payload}")
            pause("Payload Generated")
        write_payload(line, payload, 64)
        if(debug): pause("Payload Written")
        return
        


def load_config(self, filepath):
        print('loading config...')
        config = ConfigParser()
        config.read(filepath)
        for c in config.sections():
            print(config[c])
            for k in config[c].keys():
                print(k)
                if hasattr(self, k):
                    print(f'Found attribute {k}')
                    temp_attr = getattr(self, k)
                    if type(temp_attr) is list:
                        temp_cfg = config[c][k].strip('[]').split(',')
                        for i in range(2): temp_attr[i].value = int(temp_cfg[i], 0)
                    else:
                        print(config[c][k])
                        temp_attr.value = int(config[c][k], 0)
                    setattr(self, k, temp_attr)
                    print(getattr(self, k))

''' 
Write Transaction Format:       Read Transaction Format:
Sync + Reserved                 Sync + Reserved
Node Address                    Node Address
Register Address                Register Address
Data                            CRC
CRC                             Stop
Stop                            

Read Reply Format:
Sync + Reserved
Node Address
Register Address
Data
CRC
Stop

'''

def generate_crc_32(data):
    ''' Generates a cyclic redundancy check for a given data block.
    For the purposes of the data, it includes the entirety of the payload.

    Done according to the given example on page 27 of the TMC5240 manual

    Arguments:\n
    data -- the payload containing sync, DNC, node address, register address, and (optionally) data. Restricted to 24 bits.  CRC should be appended to given data resulting it 32 bits

    Returns:\n
    crc --  the crc to be appended to the data 
    '''
    #for i in range(2,-1, -1):
    #    byte = data & 0b1111_1111 << i
    crc = 0
    datagram = [
        (data >> 24) & 0x0000_00FF, 
        (data >> 16) & 0x0000_00FF, 
        (data >> 8) & 0x0000_00FF, 
        (data & 0x0000_00FF)
        ]
    for byte in datagram:
        for _ in range(0, 8):
            if(crc >> 7) ^ (byte & 0x0000_0001):
                crc = ((crc << 1) ^ 0x0000_0007) & 0x0000_00FF
            else:
                crc = (crc << 1) & 0x0000_00FF
            byte = byte >> 1
    return crc

def generate_crc_64(data):
    ''' Generates a cyclic redundancy check for a given data block.
    For the purposes of the data, it includes the entirety of the payload.

    Done according to the given example on page 27 of the TMC5240 manual

    Arguments:\n
    data -- the payload containing sync, DNC, node address, register address, and (optionally) data. Restricted to 54 bits. CRC should be appended to given data resulting it 64 bits.

    Returns:\n
    crc --  the crc to be appended to the data 
    '''
    crc = 0
    datagram = [
        (data >> 56) & 0x0000_00FF,
        (data >> 48) & 0x0000_00FF,
        (data >> 40) & 0x0000_00FF,
        (data >> 32) & 0x0000_00FF,
        (data >> 24) & 0x0000_00FF, 
        (data >> 16) & 0x0000_00FF, 
        (data >> 8) & 0x0000_00FF, 
        (data & 0x0000_00FF)
        ]
    for byte in datagram:
        for _ in range(0, 8):
            if(crc >> 7) ^ (byte & 0x0000_0001):
                crc = ((crc << 1) ^ 0x0000_0007) & 0x0000_00FF
            else:
                crc = (crc << 1) & 0x0000_00FF
            byte = byte >> 1
    return crc


def generate_write_payload(drv, addr, data):
    ''' Creates the payload for a write request to be written to the GPIO line

    Arguments:
    drv -- the TMC driver object that will be written to
    addr -- the register that is desired to be written to
    data -- the data to be written to the driver. Must be 32 bits.

    Returns:
    payload -- a payload to be used by write_payload()
    '''
    payload = SYNC
    payload = (payload << 4) | RESERVED
    payload = (payload << 8) | drv.addr
    payload = (payload << 8) | ((addr | 0x80) << 1) | 1
    payload = (payload << 32) | data
    crc = generate_crc_64(payload)
    payload = (payload << 8) | (crc & 0x0000_00FF)
    return payload

def generate_read_payload(drv, addr):
    ''' Creates the payload for a read request to be written to the GPIO line

    Arguments:\n
    drv -- the TMC driver object that will be written to\n
    addr -- the register that is desired to be written to\n

    Returns:\n
    payload -- a payload to be used by write_payload()\n
    '''
    payload = SYNC
    payload = (payload << 4) | RESERVED
    payload = (payload << 8) | drv.addr
    payload = (payload << 8) | (addr << 1)
    crc = generate_crc_32(payload)
    payload = (payload << 8) | (crc & 0x0000_00FF)
    return payload

def write_payload(line, payload, length):
    '''Writes a given payload to the desired GPIO line

    Arguments:\n
    line -- gpiod Line Object\n
    payload -- the data desired to be written to the line\n
    '''
    line.set_direction_output(True)
    #line.set_value(True)
    #time.sleep(0.5) # Let the interface reset
    for i in range(length-1, -1, -1):
        if payload & 0b1 << i:
            line.set_value(True)
        else:
            line.set_value(False)
        time.sleep(BAUD)
    line.set_value(True) #Reset Line to idle state (HIGH) (Also technically the Stop-Bit)
    return

def read_reply(line):
    '''Read a reply from the driver.

    Arguments:\n
    line -- gpiod Line object\n
    \n
    Returns:\n
    reply -- the data read from the line.\n
    '''
    line.set_direction_input()
    time.sleep(8*BAUD)
    reply = 0
    for _ in range(64):
        reply = (reply << 1) | line.get_value()
        time.sleep(BAUD)
    line.set_direction_output(True)
    crc = generate_crc_64(reply >> 8)
    if (crc != (reply & 0x0000_00FF)):
        print(f"ERROR: Reply CRC does not match: {hex(crc & 0x0000_00FF)},({crc & 0x0000_00FF}) vs. {hex(reply & 0x0000_00FF)}, ({reply & 0x0000_00FF}) ")
    return reply
    
def pause(msg):
    reply = input(f"{msg}: Press <Enter> to continue.")
        
