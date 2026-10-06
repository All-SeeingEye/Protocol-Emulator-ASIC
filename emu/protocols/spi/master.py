program = [
    # --------------------------------------------------
    # GPIO configuration
    # --------------------------------------------------
    ("DIR", 0, 1),                  # SCLK output
    ("DIR", 1, 1),                  # MOSI output
    ("DIR", 2, 1),                  # CS output

    ("SET", 2, 1),                  # CS inactive

    # --------------------------------------------------
    # Configure SCLK idle level from CPOL
    #
    # R4 = 0 -> SCLK idle LOW
    # R4 = 1 -> SCLK idle HIGH
    # --------------------------------------------------
    ("CMPI", 4, 0),                 # PC 4
    ("JCC", "EQ", 3),               # PC 5 -> PC 8 if CPOL = 0

    ("SET", 0, 1),                  # PC 6: CPOL = 1
    ("JUMP", 2),                    # PC 7 -> PC 9

    ("SET", 0, 0),                  # PC 8: CPOL = 0

    # --------------------------------------------------
    # Start transaction
    # --------------------------------------------------
    ("SET", 2, 0),                  # PC 9: assert CS

    # --------------------------------------------------
    # Select CPOL family
    # --------------------------------------------------
    ("CMPI", 4, 0),                 # PC 10
    ("JCC", "EQ", 4),               # PC 11 -> PC 15 for CPOL = 0

    # CPOL = 1: select CPHA
    ("CMPI", 5, 0),                 # PC 12
    ("JCC", "EQ", 21),              # PC 13 -> PC 34: Mode 2
    ("JUMP", 28),                   # PC 14 -> PC 42: Mode 3

    # CPOL = 0: select CPHA
    ("CMPI", 5, 0),                 # PC 15
    ("JCC", "EQ", 2),               # PC 16 -> PC 18: Mode 0
    ("JUMP", 9),                    # PC 17 -> PC 26: Mode 1


    # ==================================================
    # MODE 0
    # CPOL = 0, CPHA = 0
    #
    # idle LOW
    # data before rising edge
    # sample on rising edge
    # return LOW
    # ==================================================

    ("OUT", "L", 0, 1),             # PC 18: place MOSI bit
    ("WAIT_T", 0),                   # PC 19

    ("SET", 0, 1),                  # PC 20: rising/sample edge
    ("WAIT_T", 0),                   # PC 21

    ("SET", 0, 0),                  # PC 22: falling edge

    ("SUBI", 2, 1),                 # PC 23
    ("JCC", "NE", -6),              # PC 24 -> PC 18
    ("JUMP", 25),                   # PC 25 -> PC 50


    # ==================================================
    # MODE 1
    # CPOL = 0, CPHA = 1
    #
    # idle LOW
    # rising edge first
    # change data
    # sample on falling edge
    # ==================================================

    ("SET", 0, 1),                  # PC 26: rising edge
    ("WAIT_T", 0),                   # PC 27

    ("OUT", "L", 0, 1),             # PC 28: place MOSI bit
    ("WAIT_T", 0),                   # PC 29

    ("SET", 0, 0),                  # PC 30: falling/sample edge

    ("SUBI", 2, 1),                 # PC 31
    ("JCC", "NE", -6),              # PC 32 -> PC 26
    ("JUMP", 17),                   # PC 33 -> PC 50


    # ==================================================
    # MODE 2
    # CPOL = 1, CPHA = 0
    #
    # idle HIGH
    # data before falling edge
    # sample on falling edge
    # return HIGH
    # ==================================================

    ("OUT", "L", 0, 1),             # PC 34
    ("WAIT_T", 0),                   # PC 35

    ("SET", 0, 0),                  # PC 36: falling/sample edge
    ("WAIT_T", 0),                   # PC 37

    ("SET", 0, 1),                  # PC 38: rising edge

    ("SUBI", 2, 1),                 # PC 39
    ("JCC", "NE", -6),              # PC 40 -> PC 34
    ("JUMP", 9),                    # PC 41 -> PC 50


    # ==================================================
    # MODE 3
    # CPOL = 1, CPHA = 1
    #
    # idle HIGH
    # falling edge first
    # change data
    # sample on rising edge
    # ==================================================

    ("SET", 0, 0),                  # PC 42: falling edge
    ("WAIT_T", 0),                   # PC 43

    ("OUT", "L", 0, 1),             # PC 44
    ("WAIT_T", 0),                   # PC 45

    ("SET", 0, 1),                  # PC 46: rising/sample edge

    ("SUBI", 2, 1),                 # PC 47
    ("JCC", "NE", -6),              # PC 48 -> PC 42
    ("JUMP", 1),                    # PC 49 -> PC 50


    # --------------------------------------------------
    # End transaction
    # --------------------------------------------------
    ("SET", 2, 1),                  # PC 50: deassert CS
    ("HALT",),                      # PC 51
]