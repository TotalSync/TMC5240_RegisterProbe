from tmc5240 import *
import gpiod

chip = gpiod.Chip("/dev/gpiochip4")
line = chip.get_line(4)
if line.is_used():
    print(f"Line is in use. Consumer: {line.consumer()}")
else:
    line.request("motor-driver-interface")
    
    
    
    
    
    
    motor_driver = TMC5240()