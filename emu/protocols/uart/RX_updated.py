# UART receiver: 8N1, 10 CPU cycles per bit, GPIO3 input.
# Standalone GUI testbench sends byte 0x55 with the start bit at cycle 20.
# The firmware itself is data-independent: any byte at this bit rate works.
# This uses the updated IN R (insert at bit 31, shift right) and WAIT_PIN.
initial_gpio = [0, 0, 0, 1, 0, 0, 0, 0]  # RX input idle high
external_events = [
    (20, 3, 0),  # start
    (30, 3, 1),  # D0 = 1
    (40, 3, 0),  # D1 = 0
    (50, 3, 1),  # D2 = 1
    (60, 3, 0),  # D3 = 0
    (70, 3, 1),  # D4 = 1
    (80, 3, 0),  # D5 = 0
    (90, 3, 1),  # D6 = 1
    (100, 3, 0), # D7 = 0
    (110, 3, 1), # stop
]
program = [
    ("DIR", 3, 0),
    ("MOV", 0, 0),
    ("WAIT_PIN", 3, 0, "FALL", 100),  # start edge at cycle 20
    ("WAIT", 14),                    # D0 sample at cycle 35

    ("IN", "R", 0, 3),  # D0
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D1
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D2
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D3
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D4
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D5
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D6
    ("WAIT", 9),
    ("IN", "R", 0, 3),  # D7

    ("SHIFT", "R", 0, 24), # move byte down to R0[7:0]
    ("WAIT", 8),          # stop-bit midpoint at cycle 115
    ("WAIT_PIN", 3, 1, "CHECK"),
    ("HALT",),
]
