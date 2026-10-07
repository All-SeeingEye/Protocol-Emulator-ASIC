from cpu import *

# ============================================================
# Every instruction below is fully responsible for its own
# PC and cycle update. simulator.execute() only decodes.
# ============================================================

# helper functions for cleaner code
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

def _check_timer(timer) -> int:
    _int("Timer register", timer)

    if not 0 <= timer < TIMER_COUNT:
        raise ValueError(f"Invalid timer register: T{timer}")

    return timer

def _set_add_flags(cpu: CPU, a: int, b: int, result: int) -> None:
    cpu.flags &= ~(FLAG_Z | FLAG_N | FLAG_C | FLAG_V)
    result_masked = result & REG_MASK

    if result_masked == 0:
        cpu.flags |= FLAG_Z
    if result_masked & (1 << (REG_WIDTH - 1)):
        cpu.flags |= FLAG_N
    if result > REG_MASK:
        cpu.flags |= FLAG_C

    sign_bit = 1 << (REG_WIDTH - 1)
    if (~(a ^ b) & (a ^ result_masked) & sign_bit) != 0:
        cpu.flags |= FLAG_V

def _set_sub_flags(cpu: CPU, a: int, b: int, result: int) -> None:
    cpu.flags &= ~(FLAG_Z | FLAG_N | FLAG_C | FLAG_V)
    result_masked = result & REG_MASK

    if result_masked == 0:
        cpu.flags |= FLAG_Z
    if result_masked & (1 << (REG_WIDTH - 1)):
        cpu.flags |= FLAG_N
    if a >= b:
        cpu.flags |= FLAG_C

    sign_bit = 1 << (REG_WIDTH - 1)
    if ((a ^ b) & (a ^ result_masked) & sign_bit) != 0:
        cpu.flags |= FLAG_V

def apply_side_set(cpu: CPU, enable_mask: int, value_mask: int) -> None:
    _int("SIDE enable mask", enable_mask)
    _int("SIDE value mask", value_mask)

    if enable_mask < 0 or enable_mask >= (1 << GPIO_COUNT):
        raise ValueError("SIDE enable mask exceeds GPIO width")

    if value_mask < 0 or value_mask >= (1 << GPIO_COUNT):
        raise ValueError("SIDE value mask exceeds GPIO width")

    for pin in range(GPIO_COUNT):
        if enable_mask & (1 << pin):
            value = (value_mask >> pin) & 1

            if cpu.gpio_out[pin] != value:
                cpu.gpio_out[pin] = value
                cpu.waveform.append((cpu.cycle, pin, value))

            if cpu.gpio_dir[pin] == GPIO_OUTPUT:
                cpu.gpio[pin] = value

def apply_modifier(cpu: CPU, modifier: Optional[tuple]) -> None:
    if modifier is None:
        return

    if len(modifier) != 3:
        raise ValueError("Modifier must be ('SIDE', enable_mask, value_mask)")

    mod_ucode = modifier[0]

    if mod_ucode == "SIDE":
        gpio_enables = modifier[1]
        gpio_values = modifier[2]

        _int("SIDE enable mask", gpio_enables)
        _int("SIDE value mask", gpio_values)
        apply_side_set(cpu, gpio_enables, gpio_values)
    else:
        raise ValueError(f"Unknown instruction modifier: {mod_ucode}")

# ISA 

def set_gpio(cpu: CPU, pin: int, value: int, modifier: Optional[tuple] = None) -> None:
    _check_pin(pin)
    _check_level(value)
    apply_modifier(cpu, modifier)
    # Record only actual latch transitions.
    if cpu.gpio_out[pin] != value:
        cpu.gpio_out[pin] = value
        cpu.waveform.append((cpu.cycle, pin, value))

    if cpu.gpio_dir[pin] == GPIO_OUTPUT:
        cpu.gpio[pin] = value

    cpu.pc += 1
    cpu.cycle += 1

def load_data(cpu: CPU, register: int, value: int, modifier: Optional[tuple] = None) -> None:
    _check_reg(register)
    _int("LOAD immediate", value)
    apply_modifier(cpu, modifier)

    cpu.reg[register] = value & REG_MASK
    cpu.pc += 1
    cpu.cycle += 1

def cpu_wait(cpu: CPU, cycles: int, modifier: Optional[tuple] = None) -> None:
    _int("WAIT cycles", cycles)
    apply_modifier(cpu, modifier)
    if cycles < 0:
        raise ValueError("WAIT value cannot be negative")

    cpu.cycle += cycles
    cpu.pc += 1

def jump_offset(cpu: CPU, offset: int, modifier: Optional[tuple] = None) -> None:
    _int("JUMP offset", offset)
    apply_modifier(cpu, modifier)
    cpu.pc += offset
    cpu.cycle += 1

def cpu_halt(cpu: CPU) -> None:
    apply_modifier(cpu, modifier)
    cpu.halted = True
    cpu.cycle += 1

def register_in(cpu: CPU, direction: str, register: int, pin: int, modifier: Optional[tuple] = None) -> None:

    if direction not in ("L", "R"):
        raise ValueError("IN direction must be L or R")

    _check_reg(register)
    _check_pin(pin)
    apply_modifier(cpu, modifier)
    bit = cpu.gpio[pin]

    if bit not in (0, 1):
        raise ValueError("Invalid GPIO value")

    if direction == "R":
        # Shift right, insert sampled bit at MSB.
        cpu.reg[register] = ((cpu.reg[register] >> 1) | (bit << (REG_WIDTH - 1))) & REG_MASK

    else:
        # Shift left, insert sampled bit at LSB.
        cpu.reg[register] = ( (cpu.reg[register] << 1) | bit) & REG_MASK

    cpu.pc += 1
    cpu.cycle += 1

def shift_reg(cpu: CPU, direction: str, register: int, value: int, modifier: Optional[tuple] = None):
    if direction not in ("R", "L"):
        raise ValueError("Invalid shift direction")

    _check_reg(register)
    _int("Shift amount", value)
    apply_modifier(cpu, modifier)
    if not 0 <= value < REG_WIDTH:
        raise ValueError(f"Shift amount must be between 0 and {REG_WIDTH - 1}")

    if direction == "R":
        cpu.reg[register] >>= value

    else:
        cpu.reg[register] = (cpu.reg[register] << value) & REG_MASK

    cpu.pc += 1
    cpu.cycle += 1

def wait_pin(cpu: CPU,  pin: int, value: int, mode: str = "LEVEL", timeout: Optional[int] = None, modifier: Optional[tuple] = None ) -> None:

    _check_pin(pin)
    _check_level(value)
    apply_modifier(cpu, modifier)
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
    if (cpu.wait_pin_state is None or cpu.wait_pin_state["key"] != key):
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

def set_gpio_dir(cpu: CPU, pin: int, direction: int, modifier: Optional[tuple] = None):
    _check_pin(pin)
    _int("Direction", direction)
    apply_modifier(cpu, modifier)
    if direction not in (GPIO_INPUT, GPIO_OUTPUT):
        raise ValueError("Direction must be 0 or 1")

    cpu.gpio_dir[pin] = direction
    if direction == GPIO_OUTPUT:
        # Pin immediately shows the latched output value.
        cpu.gpio[pin] = cpu.gpio_out[pin]
    cpu.pc += 1
    cpu.cycle += 1

def register_out(cpu: CPU, direction: str, register: int, pin: int, modifier: Optional[tuple] = None) -> None:
    
    if direction not in ("L", "R"):
        raise ValueError("OUT direction must be L or R")

    _check_reg(register)
    _check_pin(pin)
    apply_modifier(cpu, modifier)
    if direction == "R":
        # LSB-first:
        # output bit 0, then shift register right
        bit = cpu.reg[register] & 1
        cpu.reg[register] >>= 1
    else:
        # MSB-first:
        # output bit 31, then shift register left
        bit = (cpu.reg[register] >> (REG_WIDTH - 1)) & 1
        cpu.reg[register] = (cpu.reg[register] << 1) & REG_MASK

    # Update output latch
    if cpu.gpio_out[pin] != bit:
        cpu.gpio_out[pin] = bit
        cpu.waveform.append((cpu.cycle, pin, bit))

    # Drive physical/observed pin only when configured as output
    if cpu.gpio_dir[pin] == GPIO_OUTPUT:
        cpu.gpio[pin] = bit

    cpu.pc += 1
    cpu.cycle += 1

def move_register(cpu: CPU, dst_register: int, src_register: int, modifier: Optional[tuple] = None) -> None:

    _check_reg(dst_register)
    _check_reg(src_register)
    apply_modifier(cpu, modifier)
    cpu.reg[dst_register] = cpu.reg[src_register] & REG_MASK

    cpu.pc += 1
    cpu.cycle += 1

def load_timer(cpu: CPU, timer: int, value: int, modifier: Optional[tuple] = None) -> None:
    _check_timer(timer)
    _int("Timer value", value)
    apply_modifier(cpu, modifier)
    if value < 0:
        raise ValueError("Timer value cannot be negative")

    cpu.timer[timer] = value & REG_MASK

    cpu.pc += 1
    cpu.cycle += 1

def wait_timer(cpu: CPU, timer: int, modifier: Optional[tuple] = None) -> None:
    _check_timer(timer)
    apply_modifier(cpu, modifier)
    cpu.cycle += cpu.timer[timer]
    cpu.pc += 1

def register_out_window(cpu: CPU, direction: str, register: int, pin: int,  count_register: int, timer: int, modifier: Optional[tuple] = None) -> None:

    if direction not in ("L", "R"):
        raise ValueError("OUT_W direction must be L or R")

    _check_reg(register)
    _check_pin(pin)
    _check_reg(count_register)
    _check_timer(timer)
    apply_modifier(cpu, modifier)
    key = (
        cpu.pc,
        "OUT_W",
        direction,
        register,
        pin,
        count_register,
        timer
    )

    # --------------------------------------------------
    # Start a new window
    # --------------------------------------------------
    if (cpu.window_state is None or cpu.window_state["key"] != key):
        count = cpu.reg[count_register]
        if not 1 <= count <= WINDOW_MAX:
            raise ValueError(f"OUT_W bit count must be between 1 and {WINDOW_MAX},  "f"got {count}")
        cpu.window_state = {
            "key": key,
            "bits_left": count,
            "delay_left": 0,
        }

    state = cpu.window_state

    # --------------------------------------------------
    # Inter-bit wait
    # --------------------------------------------------
    if state["delay_left"] > 0:
        state["delay_left"] -= 1
        cpu.cycle += 1
        if (state["delay_left"] == 0 and state["bits_left"] == 0):
            cpu.pc += 1
            cpu.window_state = None
        return
    # --------------------------------------------------
    # Send next bit
    # --------------------------------------------------
    if direction == "R":
        # LSB-first
        bit = cpu.reg[register] & 1
        cpu.reg[register] >>= 1
    else:
        # MSB-first
        bit = (cpu.reg[register] >> (REG_WIDTH - 1)) & 1
        cpu.reg[register] = (cpu.reg[register] << 1) & REG_MASK
    # Update output latch
    if cpu.gpio_out[pin] != bit:
        cpu.gpio_out[pin] = bit

        cpu.waveform.append((cpu.cycle, pin, bit))

    # Drive actual pin only if configured OUTPUT
    if cpu.gpio_dir[pin] == GPIO_OUTPUT:
        cpu.gpio[pin] = bit

    state["bits_left"] -= 1
    # Full delay after this bit
    state["delay_left"] = cpu.timer[timer]
    cpu.cycle += 1
    # Handle zero-delay final bit
    if ( state["bits_left"] == 0 and state["delay_left"] == 0):
        cpu.pc += 1
        cpu.window_state = None

def register_in_window(cpu: CPU, direction: str, register: int, pin: int, count_register: int, timer: int, modifier: Optional[tuple] = None) -> None:

    if direction not in ("L", "R"):
        raise ValueError("IN_W direction must be L or R")

    _check_reg(register)
    _check_pin(pin)
    _check_reg(count_register)
    _check_timer(timer)
    apply_modifier(cpu, modifier)
    key = (
        cpu.pc,
        "IN_W",
        direction,
        register,
        pin,
        count_register,
        timer
    )

    # --------------------------------------------------
    # Start a new window
    # --------------------------------------------------
    if ( cpu.window_state is None  or cpu.window_state["key"] != key):
        count = cpu.reg[count_register]

        if not 1 <= count <= WINDOW_MAX:
            raise ValueError(f"IN_W bit count must be between 1 and {WINDOW_MAX}, "f"got {count}")

        cpu.window_state = {
            "key": key,
            "bits_left": count,
            "delay_left": 0,
        }

    state = cpu.window_state

    # --------------------------------------------------
    # Inter-sample wait
    # --------------------------------------------------
    if state["delay_left"] > 0:

        state["delay_left"] -= 1
        cpu.cycle += 1

        if (state["delay_left"] == 0 and state["bits_left"] == 0 ):
            cpu.pc += 1
            cpu.window_state = None
        return
    # --------------------------------------------------
    # Sample next bit
    # --------------------------------------------------
    bit = cpu.gpio[pin]
    if bit not in (0, 1):
        raise ValueError("Invalid GPIO value")
    if direction == "R":
        cpu.reg[register] = ((cpu.reg[register] >> 1) | (bit << (REG_WIDTH - 1))) & REG_MASK
    else:
        cpu.reg[register] = ((cpu.reg[register] << 1) | bit ) & REG_MASK

    state["bits_left"] -= 1
    state["delay_left"] = cpu.timer[timer]
    cpu.cycle += 1

    if (state["bits_left"] == 0 and state["delay_left"] ==  0):
        cpu.pc += 1
        cpu.window_state = None

def compare_registers(cpu: CPU, reg_a: int, reg_b: int, modifier: Optional[tuple] = None) -> None:

    _check_reg(reg_a)
    _check_reg(reg_b)
    apply_modifier(cpu, modifier)
    a = cpu.reg[reg_a] & REG_MASK
    b = cpu.reg[reg_b] & REG_MASK

    result = (a - b) & REG_MASK

    # Clear previous comparison flags
    _set_sub_flags(cpu, a, b, result)

    # --------------------------------------------------
    # Z: result == 0
    # --------------------------------------------------
    if result == 0:
        cpu.flags |= FLAG_Z

    # --------------------------------------------------
    # N: MSB of result
    # --------------------------------------------------
    if result & (1 << (REG_WIDTH - 1)):
        cpu.flags |= FLAG_N

    # --------------------------------------------------
    # C: no borrow for subtraction
    #
    # a >= b => C = 1
    # --------------------------------------------------
    if a >= b:
        cpu.flags |= FLAG_C

    # --------------------------------------------------
    # V: signed overflow
    # --------------------------------------------------
    sign_bit = 1 << (REG_WIDTH - 1)

    overflow = (((a ^ b) & (a ^ result) & sign_bit) != 0)

    if overflow:
        cpu.flags |= FLAG_V
    cpu.pc += 1
    cpu.cycle += 1

def compare_immediate( cpu: CPU, register: int, immediate: int, modifier: Optional[tuple] = None) -> None:
    _check_reg(register)
    _int("CMP immediate", immediate)
    apply_modifier(cpu, modifier)
    a = cpu.reg[register] & REG_MASK
    b = immediate & REG_MASK

    result = (a - b) & REG_MASK

    cpu.flags = 0

    if result == 0:
        cpu.flags |= FLAG_Z
    if result & (1 << (REG_WIDTH - 1)):
        cpu.flags |= FLAG_N
    if a >= b:
        cpu.flags |= FLAG_C

    sign_bit = 1 << (REG_WIDTH - 1)
    overflow = (((a ^ b) & (a ^ result) & sign_bit) != 0)

    if overflow:
        cpu.flags |= FLAG_V

    cpu.pc += 1
    cpu.cycle += 1

def conditional_jump(cpu: CPU, condition: str, offset: int, modifier: Optional[tuple] = None) -> None:

    _int("JCC offset", offset)
    apply_modifier(cpu, modifier)
    z = bool(cpu.flags & FLAG_Z)
    n = bool(cpu.flags & FLAG_N)
    c = bool(cpu.flags & FLAG_C)
    v = bool(cpu.flags & FLAG_V)

    if condition == "EQ":
        take = z
    elif condition == "NE":
        take = not z

    # -------------------------
    # Signed comparisons
    # -------------------------

    elif condition == "LT":
        take = n != v
    elif condition == "LE":
        take = z or (n != v)
    elif condition == "GT":
        take = (not z) and (n == v)
    elif condition == "GE":
        take = n == v

    # -------------------------
    # Unsigned comparisons
    # -------------------------

    elif condition == "ULT":
        take = not c
    elif condition == "ULE":
        take = (not c) or z
    elif condition == "UGT":
        take = c and not z
    elif condition == "UGE":
        take = c
    else:
        raise ValueError(f"Invalid JCC condition: {condition}")

    if take:
        cpu.pc += offset
    else:
        cpu.pc += 1

    cpu.cycle += 1

def add_register(cpu: CPU, dst: int, src: int, modifier: Optional[tuple] = None ) -> None:
    _check_reg(dst)
    _check_reg(src)
    apply_modifier(cpu, modifier)
    a = cpu.reg[dst] & REG_MASK
    b = cpu.reg[src] & REG_MASK
    result = a + b

    cpu.reg[dst] = result & REG_MASK
    _set_add_flags(cpu, a, b, result)

    cpu.pc += 1
    cpu.cycle += 1

def add_immediate(cpu: CPU, dst: int, immediate: int, modifier: Optional[tuple] = None) -> None:
    _check_reg(dst)
    _int("ADDI immediate", immediate)
    apply_modifier(cpu, modifier)
    a = cpu.reg[dst] & REG_MASK
    b = immediate & REG_MASK
    result = a + b

    cpu.reg[dst] = result & REG_MASK
    _set_add_flags(cpu, a, b, result)

    cpu.pc += 1
    cpu.cycle += 1

def sub_register(cpu: CPU, dst: int, src: int, modifier: Optional[tuple] = None) -> None:
    _check_reg(dst)
    _check_reg(src)
    apply_modifier(cpu, modifier)
    a = cpu.reg[dst] & REG_MASK
    b = cpu.reg[src] & REG_MASK
    result = a - b

    cpu.reg[dst] = result & REG_MASK
    _set_sub_flags(cpu, a, b, result)

    cpu.pc += 1
    cpu.cycle += 1

def sub_immediate(cpu: CPU, dst: int, immediate: int, modifier: Optional[tuple] = None) -> None:
    _check_reg(dst)
    _int("SUBI immediate", immediate)
    apply_modifier(cpu, modifier)
    a = cpu.reg[dst] & REG_MASK
    b = immediate & REG_MASK
    result = a - b

    cpu.reg[dst] = result & REG_MASK
    _set_sub_flags(cpu, a, b, result)

    cpu.pc += 1
    cpu.cycle += 1

def clock_edge(cpu: CPU, pin: int, edge: str, modifier: Optional[tuple] = None) -> None:
    _check_pin(pin)
    apply_modifier(cpu, modifier)
    if edge not in ("LEAD", "TRAIL"):
        raise ValueError("CLK edge must be LEAD or TRAIL")

    if edge == "LEAD":
        value = 1 - cpu.cpol
    else:
        value = cpu.cpol

    if cpu.gpio_out[pin] != value:
        cpu.gpio_out[pin] = value
        cpu.waveform.append((cpu.cycle, pin, value))

    if cpu.gpio_dir[pin] == GPIO_OUTPUT:
        cpu.gpio[pin] = value

    cpu.pc += 1
    cpu.cycle += 1

