from pathlib import Path
from engine import simulate_dual
from cpu import CPU
from isa import apply_atomic

wiring = [(pin, pin, 1 if pin == 2 else 0) for pin in range(4)]
result = simulate_dual(Path('TX.py').read_text(), Path('RX_atomic.py').read_text(), wiring, max_cycles=1000)
assert result.error is None, result.error
assert result.core('TX').cpu.reg[1] == 0x3C
assert result.core('RX').cpu.reg[1] == 0xA5
assert result.core('RX').cpu.reg[2] == 0
assert result.cycles == 52

cpu = CPU()
try:
    apply_atomic(cpu, (("IN", "L", 1, 0), ("SUBI", 1, 1)))
except ValueError as exc:
    assert 'write conflict' in str(exc)
else:
    raise AssertionError('Conflicting register writes should be rejected')
print('PASS: dual SPI at HALF_PERIOD=0; TX=0x3C, RX=0xA5, 52 cycles; atomic conflict rejected')
