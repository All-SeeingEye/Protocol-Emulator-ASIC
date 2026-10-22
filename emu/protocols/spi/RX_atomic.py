# SPI mode 0 slave: edge-triggered atomic sample/count and shift/output.
SCLK = 0
MOSI = 1
CS = 2
MISO = 3
DATA = 0x3C << 24
BITS = 8
R_TX = 0
R_RX = 1
R_COUNT = 2

program = [
    ("DIR", SCLK, 0),
    ("DIR", MOSI, 0),
    ("DIR", CS, 0),
    ("DIR", MISO, 1),
    ("LOAD", R_TX, DATA),
    ("LOAD", R_RX, 0),
    ("LOAD", R_COUNT, BITS),
    ("WAIT_PIN", CS, 0, "LEVEL"),
    ("OUT", "L", R_TX, MISO),    # Mode 0: preload first MISO bit before rising edge
    # PC 9: IN and decrement happen atomically on the same observed rise.
    ("WAIT_PIN", SCLK, 1, "RISE", ("ATOMIC", (
        ("IN", "L", R_RX, MOSI),
        ("SUBI", R_COUNT, 1),
    ))),
    ("JCC", "EQ", 3),            # PC 10 -> PC 13 after the eighth sample
    ("WAIT_PIN", SCLK, 0, "FALL", ("ATOMIC", (
        ("OUT", "L", R_TX, MISO),
    ))),
    ("JUMP", -3),                # PC 12 -> PC 9
    ("WAIT_PIN", SCLK, 0, "FALL"),
    ("WAIT_PIN", CS, 1, "LEVEL"),
    ("HALT",),
]
