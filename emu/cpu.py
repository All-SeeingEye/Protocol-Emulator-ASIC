from dataclasses import dataclass, field
from typing import Optional

# ============================================================
# CPU STATE
# ============================================================
REG_WIDTH = 32
REG_MASK = (1 << REG_WIDTH) - 1
REG_COUNT = 8
GPIO_COUNT = 8

GPIO_INPUT = 0
GPIO_OUTPUT = 1

TIMER_COUNT = 4
WINDOW_MAX = 8

FLAG_Z = 1 << 0    # Zero
FLAG_N = 1 << 1    # Negative
FLAG_C = 1 << 2    # Carry / no-borrow
FLAG_V = 1 << 3    # Signed overflow

@dataclass
class CPU:
    # Program counter
    pc: int = 0

    # 8 general-purpose registers: R0-R7
    reg: list[int] = field(default_factory=lambda: [0] * REG_COUNT)

    # Observed pin level: what IN / WAIT_PIN sample and what the waveform shows.
    #   OUTPUT pin -> equals gpio_out[pin] (the CPU drives it)
    #   INPUT  pin -> written by the simulation engine from the connected wire
    gpio: list[int] = field(default_factory=lambda: [0] * GPIO_COUNT)

    # Output latch written by SET. Only reaches the pin while the pin is OUTPUT,
    # so a value can be pre-loaded before a DIR switch (useful for open-drain
    # style buses such as I2C).
    gpio_out: list[int] = field(default_factory=lambda: [0] * GPIO_COUNT)

    # GPIO direction: 0 = INPUT, 1 = OUTPUT
    gpio_dir: list[int] = field(default_factory=lambda: [0] * GPIO_COUNT)

    # Pin levels observed during the previous cycle. Maintained by the engine and
    # used by WAIT_PIN RISE/FALL so an edge on the very first sampled cycle is
    # not missed. None when running without the engine.
    gpio_prev: Optional[list[int]] = None

    # Protocol time
    cycle: int = 0

    # CPU state
    halted: bool = False
    # The state is temporary and is cleared when the instruction completes.
    wait_pin_state: Optional[dict] = None

    # Records output-latch transitions made by SET: (cycle, pin, value)
    waveform: list[tuple[int, int, int]] = field(default_factory=list)

    # Non-fatal diagnostics (e.g. SET on a pin configured as INPUT)
    warnings: list[str] = field(default_factory=list)

    # 4 general-purpose timing registers: T0-T3
    timer: list[int] = field(default_factory=lambda: [0] * TIMER_COUNT)

    # Comparison / ALU flags
    flags: int = 0
