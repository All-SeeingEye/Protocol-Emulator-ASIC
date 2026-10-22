# SPI Mode 0 master — compatible with current SIDE/DELAY ISA.
SCLK = 0
MOSI = 1
CS = 2
MISO = 3
DATA = 0xA5 << 24
BITS = 8
R_TX = 0
R_RX = 1
R_COUNT = 2
SCLK_MASK = 1 << SCLK
CS_MASK = 1 << CS
CTRL_MASK = SCLK_MASK | CS_MASK
HALF_PERIOD = 0  # Atomic RX actions let this test run without extra delay cycles.

program = [
    # Preload idle levels before output-enable to avoid an active-low CS glitch.
    ("NOP", ("SIDE", CTRL_MASK, CS_MASK)),
    ("DIR", SCLK, 1),
    ("DIR", MOSI, 1),
    ("DIR", CS, 1),
    ("DIR", MISO, 0),
    ("LOAD", R_TX, DATA),
    ("LOAD", R_RX, 0),
    ("LOAD", R_COUNT, BITS),
    ("NOP", ("SIDE", CTRL_MASK, 0)),

    # PC9 — output bit while SCLK low.
    ("OUT", "L", R_TX, MOSI, (("SIDE", SCLK_MASK, 0), ("DELAY", HALF_PERIOD))),
    # PC10 — sample on rising edge, after low setup interval.
    ("NOP", (("SIDE", SCLK_MASK, SCLK_MASK), ("DELAY", HALF_PERIOD))),
    # PC11 — input sampled while high.
    ("IN", "L", R_RX, MISO),
    # PC12 — end high phase and decrement counter.
    ("SUBI", R_COUNT, 1, (("SIDE", SCLK_MASK, 0), ("DELAY", HALF_PERIOD))),
    # PC13 — jump back to PC9.
    ("JCC", "NE", -4),
    ("NOP", ("SIDE", CTRL_MASK, CS_MASK)),
    ("HALT",)
]
