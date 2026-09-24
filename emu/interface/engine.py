"""Cycle-resolved GUI runner built on the user's existing ISA executor."""
import ast
from dataclasses import dataclass
from cpu import CPU
from simulator import execute


def parse_program(source: str):
    """Read declarative Python program data without executing uploaded Python code."""
    tree = ast.parse(source)
    assignments = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in ('program', 'external_events', 'initial_gpio', 'initial_gpio_dir', 'initial_regs'):
                    assignments[target.id] = ast.literal_eval(node.value)
    if 'program' not in assignments:
        raise ValueError('Define program = [("DIR", 0, 1), ...] in the uploaded .py file.')
    program = assignments['program']
    if not isinstance(program, (list, tuple)) or not all(isinstance(i, (tuple, list)) and i and isinstance(i[0], str) for i in program):
        raise ValueError('program must be a list of instruction tuples.')
    events = assignments.get('external_events', [])
    if not isinstance(events, (list, tuple)):
        raise ValueError('external_events must be a list of (cycle, pin, value) tuples.')
    normalized = []
    for event in events:
        if not isinstance(event, (tuple, list)) or len(event) != 3:
            raise ValueError('Each external event must be (cycle, pin, value).')
        cycle, pin, value = event
        if type(cycle) is not int or cycle < 0 or type(pin) is not int or not 0 <= pin < 8 or type(value) is not int or value not in (0, 1):
            raise ValueError(f'Invalid external event: {event}')
        normalized.append((cycle, pin, value))
    normalized.sort(key=lambda x: x[0])
    return [tuple(i) for i in program], normalized, assignments


def simulate(program, events=(), max_cycles=10000, initial_gpio=None, initial_gpio_dir=None, initial_regs=None):
    cpu = CPU()
    for name, values, count in [('gpio', initial_gpio, 8), ('gpio_dir', initial_gpio_dir, 8), ('reg', initial_regs, 8)]:
        if values is not None:
            if not isinstance(values, (list, tuple)) or len(values) != count:
                raise ValueError(f'initial {name} must have {count} elements')
            setattr(cpu, name, list(values))
    events = sorted(events)
    event_index = 0
    rows = []
    instructions = 0
    def apply_events():
        nonlocal event_index
        while event_index < len(events) and events[event_index][0] <= cpu.cycle:
            _, pin, value = events[event_index]
            cpu.gpio[pin] = value
            event_index += 1
    def record(pc, opcode, cycle=None):
        rows.append({'cycle': cpu.cycle if cycle is None else cycle, 'pc': pc, 'instruction': opcode,
                     **{f'GPIO{i}': cpu.gpio[i] for i in range(8)},
                     **{f'DIR{i}': cpu.gpio_dir[i] for i in range(8)}})
    while not cpu.halted:
        if cpu.cycle >= max_cycles:
            raise TimeoutError(f'Exceeded {max_cycles} cycles (PC={cpu.pc}); try increasing the limit.')
        if not 0 <= cpu.pc < len(program):
            raise RuntimeError(f'PC {cpu.pc} outside program (length {len(program)})')
        ins = program[cpu.pc]
        pc = cpu.pc
        op = ins[0]
        instructions += 1
        if op == 'WAIT':
            if len(ins) != 2 or type(ins[1]) is not int or ins[1] < 0:
                raise ValueError('WAIT expects a nonnegative integer cycle count')
            # Use original execute for semantics, but resolve external pin events per elapsed cycle.
            duration = ins[1]
            if duration == 0:
                apply_events()
                execute(cpu, ins)
            else:
                if cpu.cycle + duration > max_cycles:
                    raise TimeoutError(f'WAIT would exceed {max_cycles} cycles (PC={pc})')
                for _ in range(duration):
                    apply_events()
                    record(pc, op)
                    cpu.cycle += 1
                cpu.pc += 1
        else:
            apply_events()
            start_cycle = cpu.cycle
            execute(cpu, ins)
            # The instruction's GPIO effects occur at its starting cycle.
            record(pc, op, cycle=start_cycle)
        if instructions > max_cycles + len(program) * 2 + 10:
            raise TimeoutError('Instruction execution limit exceeded (possible WAIT 0 loop)')
    return cpu, rows
