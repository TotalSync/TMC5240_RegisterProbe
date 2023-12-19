from dataclasses import dataclass
from spidev import SpiDev
from configparser import ConfigParser

@dataclass
class TrinamicRegister:
    address: int
    value: int
    access: str

class TMC5240:
    def __init__(self, spi_if, spi_cs, config_file = None):
        self.spi_if = spi_if
        self.spi_cs = spi_cs

        # General Config Registers
        # These Registers are 32 bits long
        self.gconf = TrinamicRegister(0x00, 0x00, 'RW')
        self.gstat = TrinamicRegister(0x01, 0x00, 'RC')
        self.ifcnt = TrinamicRegister(0x02, 0x00, '')
        self.nodeconf = TrinamicRegister(0x03, 0x00, '')
        self.io = TrinamicRegister(0x04, 0x00, '')
        self.x_comp = [
            TrinamicRegister(0x05, 0x00, ''),
            TrinamicRegister(0x06, 0x00, '')
        ]
        self.drv_conf = TrinamicRegister(0x0A, 0x00, '')
        self.global_scalar = TrinamicRegister(0x0B, 0x00, '')

        # Velocity Dependent Config Registers
        self.i_hold_i_run = TrinamicRegister(0x10, 0x00, '')
        self.t_pwr_down = TrinamicRegister(0x11, 0x00, '')
        self.t_step = TrinamicRegister(0x12, 0x00, '')
        self.t_pwm_t_hrs = TrinamicRegister(0x13, 0x00, '')
        self.t_cool_t_hrs = TrinamicRegister(0x14, 0x00, '')
        self.t_high = TrinamicRegister(0x15, 0x00, '')

        # Ramp Generator Registers
        self.ramp_mode = TrinamicRegister(0x20, 0x00, '')
        self.x_act = TrinamicRegister(0x21, 0x00, '')
        self.v_act = TrinamicRegister(0x22, 0x00, '')
        self.v_start = TrinamicRegister(0x23, 0x00, '')
        self.a1 = TrinamicRegister(0x24, 0x00, '')
        self.v1 = TrinamicRegister(0x25, 0x00, '')
        self.a_max = TrinamicRegister(0x26, 0x00, '')
        self.v_max = TrinamicRegister(0x27, 0x00, '')
        self.d_max = TrinamicRegister(0x28, 0x00, '')
        self.tv_max = TrinamicRegister(0x29, 0x00, '')
        self.d1 = TrinamicRegister(0x2A, 0x00, '')
        self.v_stop = TrinamicRegister(0x2B, 0x00, '')
        self.t_zero_wait = TrinamicRegister(0x2C, 0x00, '')
        self.x_target = TrinamicRegister(0x2D, 0x00, '')
        self.v2 = TrinamicRegister(0x2E, 0x00, '')
        self.a2 = TrinamicRegister(0x2F, 0x00, '')
        self.d2 = TrinamicRegister(0x30, 0x00, '')


        # Ramp Generator Driver Feature Control Registers
        self.vdc_min = TrinamicRegister(0x33, 0x00, '')
        self.sw_mode = TrinamicRegister(0x34, 0x00, '')
        self.ramp_stat = TrinamicRegister(0x35, 0x00, '')
        self.x_latch = TrinamicRegister(0x36, 0x00, '')

        # Encoder Registers
        self.enc_mode = TrinamicRegister(0x38, 0x00, '')
        self.x_enc = TrinamicRegister(0x39, 0x00, '')
        self.enc_const = TrinamicRegister(0x3A, 0x00, '')
        self.enc_stat = TrinamicRegister(0x3B, 0x00, '')
        self.enc_latch = TrinamicRegister(0x3C, 0x00, '')
        self.enc_dev = TrinamicRegister(0x3D, 0x00, '')
        self.virt_stop_l = TrinamicRegister(0x3E, 0x00, '')
        self.virt_stop_r = TrinamicRegister(0x3F, 0x00, '')

        # ADC Registers
        self.adc_vsup_ain = TrinamicRegister(0x50, 0x00, '')
        self.adc_temp = TrinamicRegister(0x51, 0x00, '')
        self.otw_ov_vth = TrinamicRegister(0x52, 0x00, '')

        # Motor Drive Registers
        self.mslut_0 = TrinamicRegister(0x60, 0x00, '')
        self.mslut_1 = TrinamicRegister(0x61, 0x00, '')
        self.mslut_2 = TrinamicRegister(0x62, 0x00, '')
        self.mslut_3 = TrinamicRegister(0x63, 0x00, '')
        self.mslut_4 = TrinamicRegister(0x64, 0x00, '')
        self.mslut_5 = TrinamicRegister(0x65, 0x00, '')
        self.mslut_6 = TrinamicRegister(0x66, 0x00, '')
        self.mslut_7 = TrinamicRegister(0x67, 0x00, '')
        self.mslut_sel = TrinamicRegister(0x68, 0x00, '')
        self.mslut_start = TrinamicRegister(0x69, 0x00, '')
        
