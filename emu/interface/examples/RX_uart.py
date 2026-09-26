# UART receiver: 8N1, LSB first, 10 cycles per bit, on GPIO0. Byte ends up in R0.
# A TX edge at cycle t is visible here at t+1 (registered outputs).
program = [
    ("DIR", 0, 0),                 # c0   GPIO0 = input
    ("WAIT_PIN", 0, 0, "FALL"),    # wait for start-bit falling edge
    ("WAIT", 14),                  # move to the middle of data bit 0
    ("IN", "R", 0, 0),             # bit0 -> MSB of R0, shifting right
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit1
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit2
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit3
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit4
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit5
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit6
    ("WAIT", 9),
    ("IN", "R", 0, 0),             # bit7
    ("WAIT", 9),
    ("WAIT_PIN", 0, 1, "CHECK"),   # stop bit must be high (else framing error)
    ("SHIFT", "R", 0, 24),         # byte from bits 31..24 down to 7..0
    ("HALT",),
]
