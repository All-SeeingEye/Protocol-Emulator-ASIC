# UART 8N1 receiver: receive 0x55 on GPIO7, 10 emulator cycles per bit.
# Upload this file directly to Protocol ISA Waveform Lab.
# Uses only literal declarations accepted by the GUI (no imports or loops).
#
# The external testbench starts the frame at cycle 20.
# Because IN R0, pin writes bit 'pin', GPIO7 lets the receiver insert each
# new bit into bit 7, then shift earlier bits right between samples.
# After eight samples, R0 contains the received byte in its low eight bits.

initial_gpio = [0, 0, 0, 0, 0, 0, 0, 1]  # RX pin idles high
external_events = [
    (20, 7, 0),   # start bit
    (30, 7, 1),   # D0 = 1
    (40, 7, 0),   # D1 = 0
    (50, 7, 1),   # D2 = 1
    (60, 7, 0),   # D3 = 0
    (70, 7, 1),   # D4 = 1
    (80, 7, 0),   # D5 = 0
    (90, 7, 1),   # D6 = 1
    (100, 7, 0),  # D7 = 0
    (110, 7, 1),  # stop bit; remains high afterward
]

program = [
    ("DIR", 3, 0),
    ("MOV", 0, 0),

    # Wait for a falling start-bit edge.
    ("WAIT_PIN", 3, 0, "FALL", 100),
    ("WAIT", 14),

    # Receive eight data bits.
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),
    ("WAIT", 9),
    ("IN", "R", 0, 3),

    # Move the completed byte into bits 7:0.
    ("SHIFT", "R", 0, 24),

    # Sample the stop bit at its midpoint.
    ("WAIT", 8),
    ("WAIT_PIN", 3, 1, "CHECK"),

    ("HALT",),
]
