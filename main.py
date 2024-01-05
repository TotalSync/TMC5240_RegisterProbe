from tmc5240 import *
import gpiod
import time

chip = gpiod.Chip("/dev/gpiochip4")
line = chip.get_line(4)
if line.is_used():
    print(f"Line is in use. Consumer: {line.consumer()}")
else:
    line.request(consumer="motor-driver-interface", type=gpiod.LINE_REQ_DIR_OUT)#, flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP)
    line.set_value(True)
    print(f"Active State: {line.active_state()}")
    drivers = [TMC5240(0x00), TMC5240(0x01), 
                 TMC5240(0x02), TMC5240(0x03),
                 TMC5240(0x04), TMC5240(0x05),
                 TMC5240(0x06), TMC5240(0x07)]
    pause("Driver Created")
    count = 0
    for driver in drivers:
        pause(f"Driver {count}")
        driver.get_gconf(line)
        count += 1
    
    #driver0.set_gconf(line, 0x0F0A_A425, debug=True)