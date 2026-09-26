from cpu import *

# ============================================================
# Every instruction below is fully responsible for its own
# PC and cycle update. simulator.execute() only decodes.
# ============================================================


def _int(name: str, value) -> int:
    # bool is a subclass of int; reject it so (SET, 0, True) is caught.
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer, got {value!r}")
    return value


def _check_pin(pin) -> int:
    _int("GPIO pin", pin)
    if not 0 <= pin < GPIO_COUNT:
        raise ValueError(f"Invalid GPIO pin: {pin}")
    return pin


def _check_reg(register) -> int:
    _int("Register", register)
    if not 0 <= register < REG_COUNT:
        raise ValueError(f"Invalid register: R{register}")
    return register


def _check_level(value) -> int:
    _int("GPIO value", value)
    if value not in (0, 1):
        raise ValueError(f"GPIO value must be 0 or 1: {value}")
    return value


# ============================================================
#    SET pin, value
#
#    Semantics:
#        GPIO_OUT[pin] <- value
#        if DIR[pin] == OUTPUT: GPIO[pin] <- value
#        (on an INPUT pin only the latch changes: pre-load before DIR)
#    Timing:
#        1 cycle
#
#    PC:
#       PC <- PC + 1
# ============================================================

def set_gpio(cpu: CPU, pin: int, value: int) -> None:
    _check_pin(pin)
    _check_level(value)

    # Record only actual latch transitions.
    if cpu.gpio_out[pin] != value:
        cpu.gpio_out[pin] = value
        cpu.waveform.append((cpu.cycle, pin, value))

    if cpu.gpio_dir[pin] == GPIO_OUTPUT:
        cpu.gpio[pin] = value

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
    _check_reg(register)
    _int("MOV immediate", value)

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
    _int("WAIT cycles", cycles)
    if cycles < 0:
        raise ValueError("WAIT value cannot be negative")

    cpu.cycle += cycles
    cpu.pc += 1

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
    _int("JUMP offset", offset)
    cpu.pc += offset
    cpu.cycle += 1

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
    cpu.cycle += 1

# ============================================================
# IN
#    IN DIRECTION REGISTER PIN
#
#    Semantics:
#        R: REG <- (REG >> 1) | (GPIO[pin] << 31)   (LSB-first receive)
#        L: REG <- (REG << 1) | GPIO[pin]           (MSB-first receive)
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

    _check_reg(register)
    _check_pin(pin)

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
    cpu.cycle += 1

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

    _check_reg(register)
    _int("Shift amount", value)

    if not 0 <= value < REG_WIDTH:
        raise ValueError(f"Shift amount must be between 0 and {REG_WIDTH - 1}")

    if direction == "R":
        cpu.reg[register] >>= value

    else:
        cpu.reg[register] = (
            cpu.reg[register] << value
        ) & REG_MASK

    cpu.pc += 1
    cpu.cycle += 1

# ============================================================
# WAIT_PIN
#    WAIT_PIN PIN VALUE [MODE] [TIMEOUT]
#
#    Semantics:
#        LEVEL: wait until GPIO[pin] == VALUE
#        FALL : wait for a 1 -> 0 transition (VALUE must be 0)
#        RISE : wait for a 0 -> 1 transition (VALUE must be 1)
#        CHECK: sample once; error if GPIO[pin] != VALUE
#               (used e.g. for UART stop-bit validation)
#
#        Each sample costs one cycle. PC advances when matched.
#        Edges are detected against the level seen in the previous
#        cycle, so an edge on the first sampled cycle is caught.
#
#    Timing:
#        1 cycle per sample
# ============================================================

def wait_pin(
    cpu: CPU,
    pin: int,
    value: int,
    mode: str = "LEVEL",
    timeout: Optional[int] = None
) -> None:

    _check_pin(pin)
    _check_level(value)

    if mode not in ("LEVEL", "FALL", "RISE", "CHECK"):
        raise ValueError("Invalid WAIT_PIN mode")

    if mode == "FALL" and value != 0:
        raise ValueError("FALL requires value 0")

    if mode == "RISE" and value != 1:
        raise ValueError("RISE requires value 1")

    if timeout is not None:
        _int("Timeout", timeout)
        if timeout < 1:
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
        if cpu.gpio_prev is not None:
            # Engine tracks the previous-cycle level: edge detection is live
            # from the very first sample, like a hardware edge detector.
            previous, armed = cpu.gpio_prev[pin], True
        else:
            # Standalone use: first sample only arms the detector.
            previous, armed = current, False
        cpu.wait_pin_state = {
            "key": key,
            "previous": previous,
            "elapsed": 0,
            "armed": armed,
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
#        0 = INPUT   (pin released; level comes from the wire)
#        1 = OUTPUT  (pin driven from the output latch)
#
#    Timing:
#        1 cycle
#
#    PC:
#        PC <- PC + 1
# ============================================================

def set_gpio_dir(cpu: CPU, pin: int, direction: int):
    _check_pin(pin)
    _int("Direction", direction)

    if direction not in (GPIO_INPUT, GPIO_OUTPUT):
        raise ValueError("Direction must be 0 or 1")

    cpu.gpio_dir[pin] = direction
    if direction == GPIO_OUTPUT:
        # Pin immediately shows the latched output value.
        cpu.gpio[pin] = cpu.gpio_out[pin]
    cpu.pc += 1
    cpu.cycle += 1
