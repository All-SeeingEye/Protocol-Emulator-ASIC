#implementing SPI 0, further modifications will be seen with SPI 1 2 3

# CS line (0 means on and 1 means off)
# We will start by wasting 10 cycles to show "off" then "on" mode for 200 cycles, changing the number after data excahnge is completed.
#starting with off
#GPIO 0 will be CS line
DIR 0 1 
SET 0 1
WAIT 10
#turning the system on
SET 0 0
WAIT 200


# SCLK
# common clock, let GPIO 1 be the clock
# new instruction TOGGLE
# it should toglle a gpio pin with the amount of cycles mentioned
DIR 1 1
TOGGLE 1 1

# MOSI (master out slave in)
DIR 2 1

# new instruction OUT to take data from register to pin
OUT 0 1 
# MISO (master in slave out)
