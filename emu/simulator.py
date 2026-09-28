from isa import *
from cpu import *

# Operand count for each opcode (including the opcode itself).
SYNTAX = {
    "SET":      ((3, 3), "('SET', pin, value)"),
    "LOAD":      ((3, 3), "('LOAD', register, immediate)"),
    "WAIT":     ((2, 2), "('WAIT', cycles)"),
    "JUMP":     ((2, 2), "('JUMP', offset)"),
    "HALT":     ((1, 1), "('HALT',)"),
    "IN":       ((4, 4), "('IN', direction, register, pin)"),
    "SHIFT":    ((4, 4), "('SHIFT', direction, register, amount)"),
    "WAIT_PIN": ((3, 5), "('WAIT_PIN', pin, value, mode?, timeout?)"),
    "DIR":      ((3, 3), "('DIR', pin, direction)"),
    "MOV":      ((3, 3), "('MOV', dst_register, src_register)"),
    "OUT":      ((4, 4), "('OUT', direction, pin, register)"),
    "LOAD_T":   ((3, 3), "('LOAD_T', timer, value)"),
    "WAIT_T":   ((2, 2), "('WAIT_T', timer)"),
    "OUT_W":    ((6, 6), "('OUT_W', direction, register, pin, count, timer)"),
    "IN_W":     ((6, 6),"('IN_W', direction, register, pin, count, timer)"),
}


def check_syntax(instruction: tuple) -> None:
    opcode = instruction[0]
    if opcode not in SYNTAX:
        raise ValueError(f"Unknown opcode: {opcode}")
    (lo, hi), usage = SYNTAX[opcode]
    if not lo <= len(instruction) <= hi:
        raise ValueError(f"{opcode} syntax: {usage}")


def execute(cpu: CPU, instruction: tuple) -> None:
    """Decode one instruction. Each ISA function updates PC and cycle itself."""
    check_syntax(instruction)
    opcode = instruction[0]

    if opcode == "SET":
        set_gpio(cpu, instruction[1], instruction[2])
    elif opcode == "LOAD":
        load_data(cpu, instruction[1], instruction[2])
    elif opcode == "WAIT":
        cpu_wait(cpu, instruction[1])
    elif opcode == "JUMP":
        jump_offset(cpu, instruction[1])
    elif opcode == "HALT":
        cpu_halt(cpu)
    elif opcode == "IN":
        register_in(cpu, instruction[1], instruction[2], instruction[3])
    elif opcode == "OUT":
        register_out(cpu, instruction[1], instruction[2], instruction[3])
    elif opcode == "SHIFT":
        shift_reg(cpu, instruction[1], instruction[2], instruction[3])
    elif opcode == "WAIT_PIN":
        pin = instruction[1]
        value = instruction[2]
        mode = instruction[3] if len(instruction) >= 4 else "LEVEL"
        timeout = instruction[4] if len(instruction) == 5 else None
        wait_pin(cpu, pin, value, mode, timeout)
    elif opcode == "DIR":
        set_gpio_dir(cpu, instruction[1], instruction[2])
    elif opcode == "MOV":
        move_register(cpu,instruction[1],instruction[2])
    elif opcode == "LOAD_T":
        load_timer(cpu, instruction[1], instruction[2])
    elif opcode == "WAIT_T":
        wait_timer( cpu, instruction[1])
    elif opcode == "OUT_W":
        register_out_window(cpu, instruction[1], instruction[2], instruction[3], instruction[4], instruction[5])
    elif opcode == "IN_W":
        register_in_window(cpu, instruction[1], instruction[2], instruction[3], instruction[4], instruction[5])


# Only for testing purpose of WAIT_PIN
def update_external_gpio(cpu: CPU):
    if cpu.cycle >= 5 and cpu.gpio_dir[3] == GPIO_INPUT:
        cpu.gpio[3] = 1


def run(cpu, program, max_cycles=1000, environment=None):
    """Simple standalone runner (no wires). The GUI uses engine.py instead."""
    while not cpu.halted:
        if cpu.cycle >= max_cycles:
            raise TimeoutError("Simulation exceeded cycle limit")

        if not 0 <= cpu.pc < len(program):
            raise RuntimeError("PC out of program bounds")

        if environment is not None:
            environment(cpu)

        execute(cpu, program[cpu.pc])

        if cpu.cycle > max_cycles:
            raise TimeoutError("Simulation exceeded cycle limit")
