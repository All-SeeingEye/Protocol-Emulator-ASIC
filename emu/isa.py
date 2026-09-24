from cpu import * 
# ============================================================
#    SET pin, value
#
#    Semantics:
#        GPIO[pin] <- value
#    Timing:
#        1 cycle
#
#    PC:
#       PC <- PC + 1
# ============================================================

def set_gpio(cpu: CPU, pin: int, value: int) -> None:
    if not 0 <= pin < 8:
        raise ValueError(f"Invalid GPIO pin: {pin}")

    if value not in (0, 1):
        raise ValueError(f"GPIO value must be 0 or 1: {value}")

    # Record only actual transitions.
    if cpu.gpio[pin] != value:
        cpu.gpio[pin] = value
        cpu.waveform.append(
            (cpu.cycle, pin, value)
        )
    cpu.pc += 1
    cpu.cycle += 1

# ============================================================
# MOV
#    MOV Rd, immediate
#
#    Semantics:
#        R[Rd] <- immediate
#
#    Timing:
#        1 cycle
#
#   PC:
#        PC <- PC + 1
# ============================================================

def move_data(cpu: CPU, register: int, value: int) -> None:
    if not 0 <= register < 8:
        raise ValueError(f"Invalid register: R{register}")

    cpu.reg[register] = value & REG_MASK
    cpu.pc += 1
    cpu.cycle += 1

# ============================================================
# WAIT
#    WAIT N
#
#    Semantics:
#        cycle <- cycle + N
#
#    Timing:
#        N cycles
#
#    PC:
#        PC <- PC + 1
# ============================================================

def cpu_wait(cpu: CPU, cycles: int) -> None:
    if cycles < 0:
        raise ValueError("WAIT value cannot be negative")

    cpu.cycle += cycles

# ============================================================
# JUMP
#    JUMP offset
#
#    Semantics:
#        PC <- PC + offset
# 
#    Timing:
#        1 cycle
# ============================================================

def jump_offset(cpu: CPU, offset: int) -> None:
    cpu.pc += offset

# ============================================================
# HALT
#    HALT
#
#    Semantics:
#        halted <- True
#
#    Timing:
#        1 cycle
# ============================================================

def cpu_halt(cpu: CPU) -> None:
    cpu.halted = True

# ============================================================
# IN
#    IN REGISTER PIN 
#
#    Semantics:
#        REGISTER[index] <- GPIO[index]
#
#    Timing:
#        1 cycle
# ============================================================

def register_in(
    cpu: CPU,
    direction: str,
    register: int,
    pin: int
) -> None:

    if direction not in ("L", "R"):
        raise ValueError("IN direction must be L or R")

    if not 0 <= register < REG_COUNT:
        raise ValueError("Invalid register")

    if not 0 <= pin < GPIO_COUNT:
        raise ValueError("Invalid GPIO pin")

    bit = cpu.gpio[pin]

    if bit not in (0, 1):
        raise ValueError("Invalid GPIO value")

    if direction == "R":
        # Shift right, insert sampled bit at MSB.
        cpu.reg[register] = (
            (cpu.reg[register] >> 1)
            | (bit << (REG_WIDTH - 1))
        ) & REG_MASK

    else:
        # Shift left, insert sampled bit at LSB.
        cpu.reg[register] = (
            (cpu.reg[register] << 1) | bit
        ) & REG_MASK

    cpu.pc += 1

# ============================================================
# SHIFT
#    SHIFT R/L REGISTER VALUE
#
#    Semantics:
#        LEFT/RIGHT shift the bits of a register
#
#    Timing:
#        1 cycle
# ============================================================

def shift_reg(cpu: CPU, direction: str, register: int, value: int):
    if direction not in ("R", "L"):
        raise ValueError("Invalid shift direction")

    if not 0 <= register < 8:
        raise ValueError("Invalid register")

    if not 0 <= value < 32:
        raise ValueError("Shift amount must be between 0 and 31")

    if direction == "R":
        cpu.reg[register] >>= value

    elif direction == "L":
        cpu.reg[register] = (
            cpu.reg[register] << value
        ) & REG_MASK
    cpu.pc += 1

# ============================================================
# WAIT_PIN
#    WAIT_PIN PIN VALUE
#
#    Semantics:
#        Wait till the GPIO pin == VALUE, waste the cycle till not equal otherwise incremnet the pc 
#
#    Timing:
#        1 cycle
# ============================================================

def wait_pin(
    cpu: CPU,
    pin: int,
    value: int,
    mode: str = "LEVEL",
    timeout: int = None
) -> None:

    if not 0 <= pin < GPIO_COUNT:
        raise ValueError("Invalid GPIO pin")

    if value not in (0, 1):
        raise ValueError("Invalid GPIO value")

    if mode not in ("LEVEL", "FALL", "RISE", "CHECK"):
        raise ValueError("Invalid WAIT_PIN mode")

    if mode == "FALL" and value != 0:
        raise ValueError("FALL requires value 0")

    if mode == "RISE" and value != 1:
        raise ValueError("RISE requires value 1")

    if timeout is not None and timeout < 1:
        raise ValueError("Timeout must be positive")

    current = cpu.gpio[pin]

    if current not in (0, 1):
        raise ValueError("Invalid sampled GPIO level")

    # A one-cycle check, used for UART stop-bit validation.
    if mode == "CHECK":
        cpu.wait_pin_state = None
        cpu.cycle += 1

        if current != value:
            raise RuntimeError(f"GPIO{pin}: expected {value}, got {current}")
        cpu.pc += 1
        return

    # Identify the current waiting instruction.
    key = (cpu.pc, pin, value, mode)

    # Initialize state on the first sampling attempt.
    if (
        cpu.wait_pin_state is None
        or cpu.wait_pin_state["key"] != key
    ):
        cpu.wait_pin_state = {
            "key": key,
            "previous": current,
            "elapsed": 0,
            "armed": False,
        }

    state = cpu.wait_pin_state
    previous = state["previous"]

    if mode == "LEVEL":
        matched = current == value

    elif mode == "FALL":
        matched = state["armed"] and previous == 1 and current == 0

    else:  # RISE
        matched = state["armed"] and previous == 0 and current == 1

    state["previous"] = current
    state["armed"] = True
    state["elapsed"] += 1

    cpu.cycle += 1

    if matched:
        cpu.pc += 1
        cpu.wait_pin_state = None
        return

    if timeout is not None and state["elapsed"] >= timeout:
        cpu.wait_pin_state = None
        raise TimeoutError(f"WAIT_PIN timed out on GPIO{pin}")
    
# ============================================================
#    DIR pin, direction
#
#    direction:
#        0 = INPUT
#        1 = OUTPUT
#
#    Timing:
#        1 cycle
# ============================================================

def set_gpio_dir(cpu: CPU, pin: int, direction: int):
    if not 0 <= pin < 8:
        raise ValueError("Invalid GPIO pin")

    if direction not in (0, 1):
        raise ValueError("Direction must be 0 or 1")

    cpu.gpio_dir[pin] = direction
    cpu.cycle += 1

