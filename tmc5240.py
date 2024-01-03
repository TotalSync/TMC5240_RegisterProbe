from dataclasses import dataclass
from serial import *
from configparser import ConfigParser



SYNC = 0b1010
RESERVED = 0b1001 # This is a DNC but is included in the CRC

@dataclass
class TrinamicRegister:
    """Address: Where in memory the registers are located
     Value: The value read/written from/to the register
     Access: What type of access the register has. Key below.
     Mask: ANDing the bits with the mask will leave the appropriate bits to write
     Access: R = Read ; W = Write ; RW = Read Write ; RC = Read Clear (write a 1 to clear)"""
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

# Reply length is 64 bits
def read_register(reg):
    recieving_data = True
    bits = 0
    while (recieving_data):
        bit = read_bit()                # Read the bit from the pin
        data = append_bit(data, bit)    # Appends new bit
        crc = serial_read_crc(crc, bit) # Continue CRC calculation
        bits += 1
        recieving_data = bits != 64
        # Wait for data?
    return data

def generate_crc(data):
    crc = 0
    for byte in data:
        for bit in byte:
            if (crc >> 7) ^ (bit & 0x01):
                crc = (crc << 1) ^ 0x07
            else:
                crc = (crc << 1)
    return crc

def serial_read_crc(data, new_bit):
    return (data << 1) | ((data & 0b1000) ^ (data & 0b0010) ^ (data & 0b0001) ^ new_bit)

def generate_write_payload(drv, addr, data):
    payload = SYNC
    payload = (payload << 4) | RESERVED
    payload = (payload << 16) | drv.address
    payload = (payload << 8) | ((addr + 0x80) << 1) | 1
    payload = (payload << 32) | data
    crc = generate_crc(payload)
    payload = (payload << 8) | crc
    return payload

def generate_read_payload(drv, addr):
    payload = SYNC
    payload = (payload << 4) | RESERVED
    payload = (payload << 16) | drv.address
    payload = (payload << 8) | ((addr) << 1) | 0
    crc = generate_crc(payload)
    payload = (payload << 8) | crc
    return payload

def write_payload():
    return

def write_bit():

    return

def read_bit():
    return

#Appends a new bit
#Shifts data left by 1 and adds the new bit by ORing
def append_bit(data, bit):
    return (data << 1) | bit
        
