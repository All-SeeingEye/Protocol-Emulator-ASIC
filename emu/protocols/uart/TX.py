# Fixed-byte UART transmitter: 0x55, 8N1, 10 CPU cycles per bit.
# Upload this file into the waveform GUI; only literal assignments are used.
# GPIO0 = TX, idle high. Start bit starts at cycle 20.
# Current ISA has no register-to-GPIO instruction, so data bits are unrolled.
initial_gpio = [1, 0, 0, 0, 0, 0, 0, 0]

program = [
    ("DIR", 0, 1),        # cycle 0: GPIO0 is output
    ("SET", 0, 1),        # cycle 1: idle high (already high)
    ("WAIT", 18),        # cycles 2..19; start bit at 20

    ("SET", 0, 0),        # cycle 20: start bit
    ("WAIT", 9),

    ("SET", 0, 1),        # cycle 30: D0 = 1
    ("WAIT", 9),
    ("SET", 0, 0),        # cycle 40: D1 = 0
    ("WAIT", 9),
    ("SET", 0, 1),        # cycle 50: D2 = 1
    ("WAIT", 9),
    ("SET", 0, 0),        # cycle 60: D3 = 0
    ("WAIT", 9),
    ("SET", 0, 1),        # cycle 70: D4 = 1
    ("WAIT", 9),
    ("SET", 0, 0),        # cycle 80: D5 = 0
    ("WAIT", 9),
    ("SET", 0, 1),        # cycle 90: D6 = 1
    ("WAIT", 9),
    ("SET", 0, 0),        # cycle 100: D7 = 0
    ("WAIT", 9),

    ("SET", 0, 1),        # cycle 110: stop bit high
    ("WAIT", 9),         # entire stop bit occupies cycles 110..119
    ("HALT",),           # cycle 120
]
