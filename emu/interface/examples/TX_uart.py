# UART transmitter: sends 0x4B ('K'), 8N1, LSB first, 10 cycles per bit, on GPIO0.
# Only literal assignments are read; this file is never executed.
program = [
    ("SET", 0, 1),     # c0   pre-load latch high (pin still INPUT -> no glitch)
    ("DIR", 0, 1),     # c1   drive GPIO0: line idles high
    ("WAIT", 9),       # c2-10 idle
    ("SET", 0, 0),     # c11  start bit
    ("WAIT", 9),
    ("SET", 0, 1),     # bit0 = 1
    ("WAIT", 9),
    ("SET", 0, 1),     # bit1 = 1
    ("WAIT", 9),
    ("SET", 0, 0),     # bit2 = 0
    ("WAIT", 9),
    ("SET", 0, 1),     # bit3 = 1
    ("WAIT", 9),
    ("SET", 0, 0),     # bit4 = 0
    ("WAIT", 9),
    ("SET", 0, 0),     # bit5 = 0
    ("WAIT", 9),
    ("SET", 0, 1),     # bit6 = 1
    ("WAIT", 9),
    ("SET", 0, 0),     # bit7 = 0
    ("WAIT", 9),
    ("SET", 0, 1),     # stop bit
    ("WAIT", 9),
    ("HALT",),
]
