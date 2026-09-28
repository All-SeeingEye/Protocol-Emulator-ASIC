program = [
    # --------------------------------------------------
    # RX pin
    # --------------------------------------------------
    ("DIR", 3, 0),

    # Clear destination register
    ("LOAD", 0, 0x00),

    # --------------------------------------------------
    # Timing
    # --------------------------------------------------
    ("LOAD_T", 0, 9),       # spacing between samples
    ("LOAD_T", 1, 14),      # start edge -> center of D0
    ("LOAD_T", 2, 9),       # remaining stop-bit spacing

    # --------------------------------------------------
    # Wait for UART start bit
    # --------------------------------------------------
    ("WAIT_PIN", 3, 0, "FALL", 1000),

    # Move to center of D0
    ("WAIT_T", 1),

    # --------------------------------------------------
    # Receive all 8 data bits
    #
    # UART is LSB first, so use R.
    # Samples exactly 8 bits.
    # --------------------------------------------------
    ("IN_W", "R", 0, 3, 8, 0),

    # After 8 IN operations, byte is in R0[31:24]
    ("SHIFT", "R", 0, 24),

    # Optional copy
    ("MOV", 1, 0),

    # --------------------------------------------------
    # Stop bit check
    # --------------------------------------------------
    ("WAIT_T", 2),
    ("WAIT_PIN", 3, 1, "CHECK"),

    ("HALT",),
]