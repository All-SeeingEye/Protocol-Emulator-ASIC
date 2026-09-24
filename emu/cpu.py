from dataclasses import dataclass, field
from typing import Optional
# ============================================================
# CPU STATE
# ============================================================
REG_WIDTH = 32
REG_MASK = (1 << REG_WIDTH) - 1
REG_COUNT = 8
GPIO_COUNT = 8
@dataclass
class CPU:
    # Program counter
    pc: int = 0

    # 8 general-purpose registers: R0-R7
    reg: list[int] = field(default_factory=lambda: [0] * 8)

    # 8 GPIO pins: GPIO0-GPIO7
    gpio: list[int] = field(default_factory=lambda: [0] * 8)

    # GPIO direction
    # Not used by ISA v0.1 yet.
    gpio_dir: list[int] = field(default_factory=lambda: [0] * 8)

    # Protocol time
    cycle: int = 0

    # CPU state
    halted: bool = False
    # The state is temporary and is cleared when the instruction completes.
    wait_pin_state: Optional[dict] = None

    # Records GPIO transitions:
    # (cycle, pin, value)
    waveform: list[tuple[int, int, int]] = field(default_factory=list)
