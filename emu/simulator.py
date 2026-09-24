from isa import *
from cpu import * 

def execute(cpu: CPU, instruction: tuple) -> None:

    opcode = instruction[0]
    if opcode == "SET":
        if len(instruction) != 3:
            raise ValueError("SET syntax: ('SET', pin, value)")
        pin = instruction[1]
        value = instruction[2]
        set_gpio(cpu, pin, value)
    elif opcode == "MOV":
        if len(instruction) != 3:
            raise ValueError("MOV syntax: ('MOV', register, immediate)")
        register = instruction[1]
        value = instruction[2]
        move_data(cpu, register, value)
    elif opcode == "WAIT":
        if len(instruction) != 2:
            raise ValueError("WAIT syntax: ('WAIT', cycles)")
        cycles = instruction[1]
        cpu_wait(cpu, cycles)
        cpu.pc += 1
    elif opcode == "JUMP":
        if len(instruction) != 2:
            raise ValueError("JUMP syntax: ('JUMP', offset)")
        offset = instruction[1]
        jump_offset(cpu, offset)
        cpu.cycle += 1
    elif opcode == "HALT":
        if len(instruction) != 1:
            raise ValueError("HALT syntax: ('HALT')")
        cpu_halt(cpu)
        cpu.cycle += 1
    elif opcode == "IN":
        if len(instruction) != 4:
            raise ValueError("IN syntax: ('IN', direction, register, pin)")
        direction = instruction[1]
        register = instruction[2]
        pin = instruction[3]
        register_in(cpu, direction, register, pin)
        cpu.cycle += 1
    elif opcode == "SHIFT":
        if len(instruction) != 4:
            raise ValueError("SHIFT syntax: ('SHIFT', direction, register, amount)")
        direction = instruction[1]
        register = instruction[2]
        value = instruction[3]

        shift_reg(cpu, direction, register, value)
        cpu.cycle += 1
    elif opcode == "WAIT_PIN":
        if not 3 <= len(instruction) <= 5:
            raise ValueError("WAIT_PIN syntax: ""('WAIT_PIN', pin, value, mode?, timeout?)")
        pin = instruction[1]
        value = instruction[2]
        mode = instruction[3] if len(instruction) >= 4 else "LEVEL"
        timeout = instruction[4] if len(instruction) == 5 else None
        wait_pin(cpu, pin, value, mode, timeout)
    elif opcode == "DIR":
        if len(instruction) != 3:
            raise ValueError("DIR syntax: ('DIR', pin, direction)")
        set_gpio_dir(cpu, instruction[1], instruction[2])
        cpu.pc += 1
    else:
        raise ValueError(f"Unknown opcode: {opcode}")

#Only for testing purpose of WAIT_IN
def update_external_gpio(cpu: CPU):
    if cpu.cycle >= 5:
        cpu.gpio[3] = 1


def run(cpu, program, max_cycles=1000, environment=None):
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