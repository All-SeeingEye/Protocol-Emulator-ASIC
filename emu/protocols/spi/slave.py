program = [
    # --------------------------------------------------
    # SPI inputs
    # --------------------------------------------------
    ("DIR", 0, 0),                  # PC 0: SCLK input
    ("DIR", 1, 0),                  # PC 1: MOSI input
    ("DIR", 2, 0),                  # PC 2: CS input

    ("LOAD", 0, 0),                 # PC 3: clear RX register

    # --------------------------------------------------
    # Wait for transaction
    # --------------------------------------------------
    ("WAIT_PIN", 2, 0, "FALL", 1000),  # PC 4

    # --------------------------------------------------
    # Determine sampling edge
    #
    # CPOL == CPHA -> rising
    # CPOL != CPHA -> falling
    # --------------------------------------------------
    ("CMP", 4, 5),                  # PC 5
    ("JCC", "EQ", 2),               # PC 6 -> PC 8
    ("JUMP", 6),                    # PC 7 -> PC 13


    # ==================================================
    # RISING-EDGE RECEIVE
    #
    # Used by:
    #   Mode 0: CPOL=0 CPHA=0
    #   Mode 3: CPOL=1 CPHA=1
    # ==================================================

    ("WAIT_PIN", 0, 1, "RISE", 1000),  # PC 8
    ("IN", "L", 0, 1),                 # PC 9

    ("SUBI", 2, 1),                    # PC 10
    ("JCC", "NE", -3),                 # PC 11 -> PC 8

    ("JUMP", 5),                       # PC 12 -> PC 17


    # ==================================================
    # FALLING-EDGE RECEIVE
    #
    # Used by:
    #   Mode 1: CPOL=0 CPHA=1
    #   Mode 2: CPOL=1 CPHA=0
    # ==================================================

    ("WAIT_PIN", 0, 0, "FALL", 1000),  # PC 13
    ("IN", "L", 0, 1),                 # PC 14

    ("SUBI", 2, 1),                    # PC 15
    ("JCC", "NE", -3),                 # PC 16 -> PC 13


    # --------------------------------------------------
    # Transaction complete
    # --------------------------------------------------
    ("MOV", 1, 0),                     # PC 17: R1 = received data

    ("WAIT_PIN", 2, 1, "RISE", 1000),  # PC 18: wait for CS release

    ("HALT",),                          # PC 19
]