from isa import *
from cpu import *
from dataclasses import dataclass, field
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
    "OUT_W":    ((6, 6),"('OUT_W', direction, register, pin, count_register, timer)"),
    "IN_W":     ((6, 6),"('IN_W', direction, register, pin, count_register, timer)"),
    "CMP":      ((3, 3),"('CMP', reg_a, reg_b)"),
    "CMPI":     ((3, 3),"('CMPI', register, immediate)"),
    "JCC":      ((3, 3),"('JCC', condition, offset)"),
    "LOOP":     ((3, 3),"('LOOP', register, offset)"),
    "ADD":      ((3, 3), "('ADD', dst_register, src_register)"),
    "ADDI":     ((3, 3), "('ADDI', dst_register, immediate)"),
    "SUB":      ((3, 3), "('SUB', dst_register, src_register)"),
    "SUBI":     ((3, 3), "('SUBI', dst_register, immediate)"),
}

def split_modifier(instruction: tuple) -> tuple[tuple, Optional[tuple]]:
    if not instruction:
        raise ValueError("Empty instruction")

    modifier = None

    if isinstance(instruction[-1], tuple):
        candidate = instruction[-1]

        if candidate and candidate[0] == "SIDE":
            if len(candidate) != 3:
                raise ValueError("SIDE modifier syntax: ('SIDE', enable_mask, value_mask)")

            modifier = candidate
            instruction = instruction[:-1]

    return instruction, modifier

def check_syntax(instruction: tuple) -> None:
    core, modifier = split_modifier(instruction)
    opcode = core[0]

    if opcode not in SYNTAX:
        raise ValueError(f"Unknown opcode: {opcode}")

    (lo, hi), usage = SYNTAX[opcode]

    if not lo <= len(core) <= hi:
        raise ValueError(f"{opcode} syntax: {usage} + optional ('SIDE', enable_mask, value_mask)")

    if modifier is not None:
        _int("SIDE enable mask", modifier[1])
        _int("SIDE value mask", modifier[2])

def execute(cpu: CPU, instruction: tuple) -> None:
    """Decode one instruction. Each ISA function updates PC and cycle itself."""
    core, modifier = split_modifier(instruction)
    opcode = core[0]

    if opcode == "SET":
        set_gpio(cpu, core[1], core[2], modifier)
    elif opcode == "LOAD":
        load_data(cpu, core[1], core[2], modifier)
    elif opcode == "WAIT":
        cpu_wait(cpu, core[1], modifier)
    elif opcode == "JUMP":
        jump_offset(cpu, core[1], modifier)
    elif opcode == "HALT":
        cpu_halt(cpu)
    elif opcode == "IN":
        register_in(cpu, core[1], core[2], core[3], modifier)
    elif opcode == "OUT":
        register_out(cpu, core[1], core[2], core[3], modifier)
    elif opcode == "SHIFT":
        shift_reg(cpu, core[1], core[2], core[3], modifier)
    elif opcode == "WAIT_PIN":
        mode = core[3] if len(core) >= 4 else "LEVEL"
        timeout = core[4] if len(core) == 5 else None
        wait_pin(cpu, core[1], core[2], mode, timeout, modifier)
    elif opcode == "DIR":
        set_gpio_dir(cpu, core[1], core[2], modifier)
    elif opcode == "MOV":
        move_register(cpu,core[1],core[2], modifier)
    elif opcode == "LOAD_T":
        load_timer(cpu, core[1], core[2], modifier)
    elif opcode == "WAIT_T":
        wait_timer( cpu, core[1], modifier)
    elif opcode == "OUT_W":
        register_out_window(cpu, core[1], core[2], core[3], core[4], core[5], modifier)
    elif opcode == "IN_W":
        register_in_window(cpu, core[1], core[2], core[3], core[4], core[5], modifier)
    elif opcode == "CMP":
        compare_registers(cpu, core[1], core[2], modifier)
    elif opcode == "CMPI":
        compare_immediate(cpu, core[1], core[2], modifier)
    elif opcode == "JCC":
        conditional_jump(cpu, core[1], core[2], modifier)
    # elif opcode == "LOOP":
    #     loop_register(cpu, core[1], core[2])
    elif opcode == "ADD":
        add_register(cpu, core[1], core[2], modifier)
    elif opcode == "ADDI":
        add_immediate(cpu, core[1], core[2], modifier)
    elif opcode == "SUB":
        sub_register(cpu, core[1], core[2], modifier)
    elif opcode == "SUBI":
        sub_immediate(cpu, core[1], core[2], modifier)
    elif opcode == "CLK":
        clock_edge(cpu, core[1], core[2], modifier)

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
