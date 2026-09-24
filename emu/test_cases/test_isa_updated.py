"""Tests for the nine instructions in cpu.py, isa.py, simulator.py.

Run: python -m pytest -v test_isa.py
Regression tests for the updated implementation.
"""
import pytest
from cpu import CPU, REG_MASK
from simulator import execute, run


# SET

def test_set_updates_pin_at_current_cycle_and_records_transition():
    cpu = CPU()
    execute(cpu, ('SET', 2, 1))
    assert (cpu.gpio[2], cpu.pc, cpu.cycle) == (1, 1, 1)
    assert cpu.waveform == [(0, 2, 1)]


def test_set_same_value_does_not_create_transition():
    cpu = CPU()
    execute(cpu, ('SET', 2, 0))
    assert cpu.waveform == []
    assert (cpu.pc, cpu.cycle) == (1, 1)


@pytest.mark.parametrize('instruction', [('SET', -1, 1), ('SET', 8, 1), ('SET', 0, 2)])
def test_set_rejects_invalid_operands(instruction):
    with pytest.raises(ValueError):
        execute(CPU(), instruction)


# MOV

def test_mov_immediate_and_cycle():
    cpu = CPU()
    execute(cpu, ('MOV', 7, 0x12345678))
    assert cpu.reg[7] == 0x12345678
    assert (cpu.pc, cpu.cycle) == (1, 1)


@pytest.mark.parametrize('register', [-1, 8])
def test_mov_rejects_invalid_register(register):
    with pytest.raises(ValueError):
        execute(CPU(), ('MOV', register, 1))


def test_mov_masks_to_32_bits():
    cpu = CPU()
    execute(cpu, ('MOV', 0, 0x1_0000_0005))
    assert cpu.reg[0] == 5


# WAIT

def test_wait_advances_exact_cycles_and_pc():
    cpu = CPU()
    execute(cpu, ('WAIT', 10))
    assert (cpu.pc, cpu.cycle) == (1, 10)


def test_wait_zero_is_allowed():
    cpu = CPU()
    execute(cpu, ('WAIT', 0))
    assert (cpu.pc, cpu.cycle) == (1, 0)


def test_wait_rejects_negative():
    with pytest.raises(ValueError):
        execute(CPU(), ('WAIT', -1))


# JUMP

@pytest.mark.parametrize('start,offset,target', [(3, 2, 5), (3, -2, 1), (3, 0, 3)])
def test_jump_is_pc_relative_and_one_cycle(start, offset, target):
    cpu = CPU(pc=start)
    execute(cpu, ('JUMP', offset))
    assert (cpu.pc, cpu.cycle) == (target, 1)


# HALT

def test_halt_stops_without_advancing_pc():
    cpu = CPU(pc=4)
    execute(cpu, ('HALT',))
    assert cpu.halted is True
    assert (cpu.pc, cpu.cycle) == (4, 1)


# IN

@pytest.mark.parametrize('pin,level', [(0, 1), (3, 1), (7, 0)])
def test_in_updates_only_corresponding_bit(pin, level):
    cpu = CPU()
    cpu.reg[2] = 0xA5A5A5A5
    cpu.gpio[pin] = level
    expected = (cpu.reg[2] & ~(1 << pin)) | (level << pin)
    execute(cpu, ('IN', 2, pin))
    assert cpu.reg[2] == expected
    assert (cpu.pc, cpu.cycle) == (1, 1)


@pytest.mark.parametrize('instruction', [('IN', -1, 0), ('IN', 8, 0), ('IN', 0, -1), ('IN', 0, 8)])
def test_in_rejects_invalid_register_or_pin(instruction):
    with pytest.raises(ValueError):
        execute(CPU(), instruction)


def test_in_rejects_extra_operands():
    with pytest.raises(ValueError):
        execute(CPU(), ('IN', 0, 0, 99))


# SHIFT

@pytest.mark.parametrize('direction,initial,amount,expected', [
    ('R', 0b10110010, 3, 0b00010110),
    ('L', 0b10110010, 2, 0b1011001000),
    ('L', 0x80000000, 1, 0),
    ('R', 0x80000000, 31, 1),
    ('L', 0x55, 0, 0x55),
])
def test_shift_result_and_one_cycle(direction, initial, amount, expected):
    cpu = CPU()
    cpu.reg[1] = initial
    execute(cpu, ('SHIFT', direction, 1, amount))
    assert cpu.reg[1] == expected
    assert (cpu.pc, cpu.cycle) == (1, 1)


@pytest.mark.parametrize('instruction', [
    ('SHIFT', 'X', 0, 1), ('SHIFT', 'R', -1, 1),
    ('SHIFT', 'L', 8, 1), ('SHIFT', 'L', 0, -1),
    ('SHIFT', 'L', 0, 32),
])
def test_shift_rejects_invalid_operands(instruction):
    with pytest.raises(ValueError):
        execute(CPU(), instruction)


def test_shift_rejects_extra_operands():
    with pytest.raises(ValueError):
        execute(CPU(), ('SHIFT', 'R', 0, 1, 99))


# WAIT_PIN

def test_wait_pin_matches_immediately():
    cpu = CPU()
    cpu.gpio[1] = 1
    execute(cpu, ('WAIT_PIN', 1, 1))
    assert (cpu.pc, cpu.cycle) == (1, 1)


def test_wait_pin_stalls_until_pin_matches():
    cpu = CPU()
    execute(cpu, ('WAIT_PIN', 1, 1))
    execute(cpu, ('WAIT_PIN', 1, 1))
    assert (cpu.pc, cpu.cycle) == (0, 2)
    cpu.gpio[1] = 1
    execute(cpu, ('WAIT_PIN', 1, 1))
    assert (cpu.pc, cpu.cycle) == (1, 3)


@pytest.mark.parametrize('instruction', [('WAIT_PIN', -1, 0), ('WAIT_PIN', 8, 0), ('WAIT_PIN', 0, 2)])
def test_wait_pin_rejects_invalid_operands(instruction):
    with pytest.raises(ValueError):
        execute(CPU(), instruction)


def test_wait_pin_rejects_extra_operands():
    with pytest.raises(ValueError):
        execute(CPU(), ('WAIT_PIN', 0, 0, 99))


# DIR

def test_dir_changes_direction_in_one_cycle():
    cpu = CPU()
    execute(cpu, ('DIR', 5, 1))
    assert cpu.gpio_dir[5] == 1
    assert (cpu.pc, cpu.cycle) == (1, 1)
    execute(cpu, ('DIR', 5, 0))
    assert cpu.gpio_dir[5] == 0
    assert (cpu.pc, cpu.cycle) == (2, 2)


@pytest.mark.parametrize('instruction', [('DIR', -1, 0), ('DIR', 8, 0), ('DIR', 0, 2)])
def test_dir_rejects_invalid_operands(instruction):
    with pytest.raises(ValueError):
        execute(CPU(), instruction)


# Integration and simulator behavior

def test_full_program_waveform_and_timing():
    cpu = CPU()
    run(cpu, [('DIR', 0, 1), ('SET', 0, 1), ('WAIT', 10), ('SET', 0, 0), ('HALT',)])
    assert cpu.waveform == [(1, 0, 1), (12, 0, 0)]
    assert (cpu.pc, cpu.cycle, cpu.halted) == (4, 14, True)


def test_run_rejects_invalid_pc():
    with pytest.raises(RuntimeError, match='PC out of program bounds'):
        run(CPU(), [('JUMP', -1)])


def test_run_times_out_on_unmet_wait_pin():
    with pytest.raises(TimeoutError):
        run(CPU(), [('WAIT_PIN', 2, 1)], max_cycles=10)


def test_run_does_not_modify_unrelated_gpio():
    cpu = CPU()
    run(cpu, [('WAIT', 6), ('HALT',)])
    assert cpu.gpio[3] == 0


def test_run_does_not_overshoot_cycle_budget():
    cpu = CPU()
    with pytest.raises(TimeoutError):
        run(cpu, [('WAIT', 100), ('HALT',)], max_cycles=10)
    assert cpu.cycle == 100  # instruction-level WAIT completes before timeout check


@pytest.mark.parametrize('instruction', [
    ('SET', 0), ('MOV', 0), ('WAIT',), ('JUMP',), ('HALT', 0), ('DIR', 0),
])
def test_existing_instruction_arity_checks(instruction):
    with pytest.raises(ValueError):
        execute(CPU(), instruction)
