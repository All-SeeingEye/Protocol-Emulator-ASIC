"""Cycle-accurate engine: runs one or more CPUs in lockstep, connected by wires.

Timing model (per global cycle t):
  1. External events scheduled for cycle t are applied.
  2. Every net (wire) is resolved from the pins driving it at the end of t-1:
       - exactly one OUTPUT pin (or several agreeing) -> that level
       - no OUTPUT pin                                -> the net's idle/pull level
       - OUTPUT pins disagreeing                      -> bus contention error
     INPUT pins then take the level of their net.
  3. Every running CPU executes one cycle of work.
So a SET on one CPU at cycle t is seen by the other CPU at cycle t+1
(registered outputs), independent of evaluation order.
"""
import ast
from dataclasses import dataclass, field
from typing import Optional

from cpu import CPU, GPIO_COUNT, REG_COUNT, REG_MASK, GPIO_OUTPUT
from simulator import execute, check_syntax

READ_KEYS = ('program', 'external_events', 'initial_gpio', 'initial_gpio_dir', 'initial_regs')


# ============================================================
# Parsing (uploaded Python is never executed)
# ============================================================

def parse_program(source: str):
    """Read declarative Python program data without executing uploaded code."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise ValueError(f'Python syntax error on line {exc.lineno}: {exc.msg}') from None

    assignments = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if node.value is None:          # bare annotation: `program: list`
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id in READ_KEYS:
                    try:
                        assignments[target.id] = ast.literal_eval(node.value)
                    except ValueError:
                        raise ValueError(
                            f'`{target.id}` (line {node.lineno}) must be a literal: only numbers, '
                            'strings, tuples and lists are allowed (no variables, loops or calls).'
                        ) from None

    if 'program' not in assignments:
        raise ValueError('Define program = [("DIR", 0, 1), ...] in the uploaded .py file.')
    program = assignments['program']
    if not isinstance(program, (list, tuple)) or not all(
            isinstance(i, (tuple, list)) and i and isinstance(i[0], str) for i in program):
        raise ValueError('program must be a list of instruction tuples, e.g. ("HALT",) '
                         '(note the trailing comma for one-element tuples).')
    program = [tuple(i) for i in program]
    for index, ins in enumerate(program):
        try:
            check_syntax(ins)
            if ins[0] == 'WAIT' and (type(ins[1]) is not int or ins[1] < 0):
                raise ValueError('WAIT expects a nonnegative integer cycle count')
        except ValueError as exc:
            raise ValueError(f'program[{index}] {ins}: {exc}') from None

    events = assignments.get('external_events', [])
    if not isinstance(events, (list, tuple)):
        raise ValueError('external_events must be a list of (cycle, pin, value) tuples.')
    normalized = []
    for event in events:
        if not isinstance(event, (tuple, list)) or len(event) != 3:
            raise ValueError('Each external event must be (cycle, pin, value).')
        cycle, pin, value = event
        if (type(cycle) is not int or cycle < 0 or type(pin) is not int or not 0 <= pin < GPIO_COUNT
                or type(value) is not int or value not in (0, 1)):
            raise ValueError(f'Invalid external event: {event}')
        normalized.append((cycle, pin, value))
    # Stable sort: for events at the same cycle, the later one in the file wins.
    normalized.sort(key=lambda x: x[0])
    return program, normalized, assignments


def _check_initial(name, values, count, allowed=None):
    if values is None:
        return None
    if not isinstance(values, (list, tuple)) or len(values) != count:
        raise ValueError(f'{name} must have {count} elements')
    for v in values:
        if type(v) is not int or (allowed is not None and v not in allowed):
            raise ValueError(f'{name} values must be {"0 or 1" if allowed else "integers"}: {v!r}')
    return list(values)


# ============================================================
# Core: one CPU + its program, advanced exactly one cycle per step()
# ============================================================

def format_instruction(ins) -> str:
    return ins[0] + (' ' + ', '.join(map(str, ins[1:])) if len(ins) > 1 else '')


class Core:
    def __init__(self, name, program, events=(), initial_gpio=None,
                 initial_gpio_dir=None, initial_regs=None):
        self.name = name
        self.program = [tuple(i) for i in program]
        self.events = sorted(events, key=lambda e: e[0])     # stable
        self.event_index = 0
        self.wait_left = 0
        self.rows = []

        cpu = CPU()
        gpio = _check_initial(f'{name} initial_gpio', initial_gpio, GPIO_COUNT, (0, 1))
        gdir = _check_initial(f'{name} initial_gpio_dir', initial_gpio_dir, GPIO_COUNT, (0, 1))
        regs = _check_initial(f'{name} initial_regs', initial_regs, REG_COUNT)
        if gpio is not None:
            cpu.gpio, cpu.gpio_out = list(gpio), list(gpio)
        if gdir is not None:
            cpu.gpio_dir = gdir
        if regs is not None:
            cpu.reg = [r & REG_MASK for r in regs]
        cpu.gpio_prev = list(cpu.gpio)       # enables live edge detection
        self.initial_gpio = list(cpu.gpio)
        self.cpu = cpu

    def step(self):
        """Execute exactly one cycle. Returns (pc, instruction) that used it."""
        cpu, program = self.cpu, self.program
        if self.wait_left == 0:
            # WAIT 0 takes no time: skip over any chain of them.
            while True:
                if not 0 <= cpu.pc < len(program):
                    raise RuntimeError(f'PC {cpu.pc} outside program (length {len(program)})')
                ins = program[cpu.pc]
                if ins[0] != 'WAIT':
                    break
                check_syntax(ins)
                if type(ins[1]) is not int or ins[1] < 0:
                    raise ValueError('WAIT expects a nonnegative integer cycle count')
                if ins[1] > 0:
                    self.wait_left = ins[1]
                    break
                cpu.pc += 1

        pc, ins = cpu.pc, program[cpu.pc]
        start = cpu.cycle
        if self.wait_left:
            # Multi-cycle WAIT is spread over cycles so the other CPU and
            # external events keep running while this one waits.
            cpu.cycle += 1
            self.wait_left -= 1
            if self.wait_left == 0:
                cpu.pc += 1
        else:
            execute(cpu, ins)
        if cpu.cycle != start + 1:
            raise RuntimeError(f'Internal timing error: {ins} advanced {cpu.cycle - start} cycles in one step')
        return pc, ins

    def record(self, t, pc, ins):
        cpu = self.cpu
        self.rows.append({
            'cycle': t, 'pc': pc, 'instruction': format_instruction(ins) if ins else '(halted)',
            **{f'GPIO{i}': cpu.gpio[i] for i in range(GPIO_COUNT)},
            **{f'DIR{i}': cpu.gpio_dir[i] for i in range(GPIO_COUNT)},
            **{f'R{i}': cpu.reg[i] for i in range(REG_COUNT)},
        })


# ============================================================
# Wires
# ============================================================

@dataclass
class Net:
    name: str
    members: list            # [(core_index, pin), ...]
    idle: int                # level when nothing drives it (pull / external level)
    level: int = 0
    driver: str = ''
    shared: bool = False


@dataclass
class SimResult:
    cores: list
    nets: list
    bus_rows: list
    cycles: int
    error: Optional[str] = None

    def core(self, name):
        return next(c for c in self.cores if c.name == name)


class System:
    def __init__(self, cores, wiring=()):
        """wiring: iterable of (pin_on_core0, pin_on_core1, idle_level)."""
        self.cores = cores
        self.nets = []
        self.pin_net = {}
        used = [set() for _ in cores]
        for entry in wiring:
            a, b, idle = entry
            for side, pin in ((0, a), (1, b)):
                if type(pin) is not int or not 0 <= pin < GPIO_COUNT:
                    raise ValueError(f'Wiring: invalid {cores[side].name} pin {pin!r}')
                if pin in used[side]:
                    raise ValueError(f'Wiring: {cores[side].name}.GPIO{pin} is connected twice')
                used[side].add(pin)
            if idle not in (0, 1):
                raise ValueError(f'Wiring: idle level must be 0 or 1, got {idle!r}')
            net = Net(f'{cores[0].name}.GPIO{a} ↔ {cores[1].name}.GPIO{b}',
                      [(0, a), (1, b)], idle, idle, shared=True)
            self._add(net)
        # Every unconnected pin gets a private net driven by its CPU or its test events.
        for k, core in enumerate(cores):
            for pin in range(GPIO_COUNT):
                if pin not in used[k]:
                    label = f'GPIO{pin}' if len(cores) == 1 else f'{core.name}.GPIO{pin}'
                    level = core.initial_gpio[pin]
                    self._add(Net(label, [(k, pin)], level, level))

    def _add(self, net):
        self.nets.append(net)
        for member in net.members:
            self.pin_net[member] = net

    def _apply_events(self, t):
        for k, core in enumerate(self.cores):
            while core.event_index < len(core.events) and core.events[core.event_index][0] <= t:
                _, pin, value = core.events[core.event_index]
                self.pin_net[(k, pin)].idle = value
                core.event_index += 1

    def _resolve(self, t):
        for net in self.nets:
            drivers = [(self.cores[k].name, self.cores[k].cpu.gpio_out[p])
                       for k, p in net.members if self.cores[k].cpu.gpio_dir[p] == GPIO_OUTPUT]
            levels = {v for _, v in drivers}
            if len(levels) > 1:
                detail = ', '.join(f'{n} drives {v}' for n, v in drivers)
                raise RuntimeError(f'Bus contention on {net.name} at cycle {t}: {detail}')
            if drivers:
                net.level, net.driver = drivers[0][1], '+'.join(n for n, _ in drivers)
            else:
                net.level, net.driver = net.idle, 'idle'
        for k, core in enumerate(self.cores):
            cpu = core.cpu
            cpu.gpio_prev = list(cpu.gpio)
            for pin in range(GPIO_COUNT):
                if cpu.gpio_dir[pin] != GPIO_OUTPUT:
                    cpu.gpio[pin] = self.pin_net[(k, pin)].level

    def run(self, max_cycles=10000) -> SimResult:
        bus_rows, error, t = [], None, 0
        current = None
        try:
            while not all(c.cpu.halted for c in self.cores):
                if t >= max_cycles:
                    running = ', '.join(f'{c.name} PC={c.cpu.pc} ({format_instruction(c.program[c.cpu.pc])})'
                                        for c in self.cores if not c.cpu.halted and 0 <= c.cpu.pc < len(c.program))
                    raise TimeoutError(f'Exceeded {max_cycles} cycles; still running: {running}. '
                                       'Increase the limit or check for a missed WAIT_PIN condition.')
                current = None
                self._apply_events(t)
                self._resolve(t)
                executed = []
                for core in self.cores:
                    current = core
                    executed.append(None if core.cpu.halted else core.step())
                current = None
                for core, done in zip(self.cores, executed):
                    pc, ins = done if done else (core.cpu.pc, None)
                    core.record(t, pc, ins)
                bus_rows.append({'cycle': t, **{n.name: n.level for n in self.nets if n.shared},
                                 **{f'{n.name} driver': n.driver for n in self.nets if n.shared}})
                t += 1
            # Settle wires once more so final INPUT levels reflect final outputs.
            self._apply_events(t)
            self._resolve(t)
        except Exception as exc:
            where = f'{current.name} @ PC {current.cpu.pc}, cycle {t}: ' if current else ''
            error = f'{where}{type(exc).__name__}: {exc}'
        return SimResult(self.cores, self.nets, bus_rows, t, error)


# ============================================================
# Public helpers used by the GUI
# ============================================================

def lint(core) -> list:
    """Post-run diagnostics that are not errors."""
    notes = list(core.cpu.warnings)
    ever_output = {p for row in core.rows for p in range(GPIO_COUNT) if row[f'DIR{p}']}
    ever_output |= {p for p in range(GPIO_COUNT) if core.cpu.gpio_dir[p]}
    for pin in sorted({p for _, p, _ in core.cpu.waveform} - ever_output):
        notes.append(f'SET was used on GPIO{pin}, but GPIO{pin} was never configured as OUTPUT, '
                     f'so nothing was driven. Add ("DIR", {pin}, 1).')
    return notes


def build_core(name, source):
    program, events, initial = parse_program(source)
    return Core(name, program, events,
                initial.get('initial_gpio'), initial.get('initial_gpio_dir'), initial.get('initial_regs'))


def simulate_single(source, max_cycles=10000) -> SimResult:
    return System([build_core('CPU', source)]).run(max_cycles)


def simulate_dual(tx_source, rx_source, wiring, max_cycles=10000) -> SimResult:
    tx = build_core('TX', tx_source)
    rx = build_core('RX', rx_source)
    return System([tx, rx], wiring).run(max_cycles)


def simulate(program, events=(), max_cycles=10000, initial_gpio=None, initial_gpio_dir=None, initial_regs=None):
    """Backward-compatible single-CPU API: returns (cpu, rows) or raises."""
    core = Core('CPU', program, events, initial_gpio, initial_gpio_dir, initial_regs)
    result = System([core]).run(max_cycles)
    if result.error:
        raise RuntimeError(result.error)
    return core.cpu, core.rows
