"""Run with: python test_engine.py"""
from engine import simulate, simulate_dual, simulate_single, parse_program, lint, build_core

TX = open('examples/TX_uart.py').read()
RX = open('examples/RX_uart.py').read()
STRAIGHT = [(p, p, 1) for p in range(8)]


def test_uart_pair():
    r = simulate_dual(TX, RX, STRAIGHT)
    assert r.error is None, r.error
    rx = r.core('RX').cpu
    assert rx.reg[0] == 0x4B, hex(rx.reg[0])
    assert r.core('RX').cpu.gpio[0] == 1           # settled idle-high line
    assert not lint(r.core('TX')) and not lint(r.core('RX'))


def test_crossed_wiring_and_other_bytes():
    # TX on GPIO5 wired to RX GPIO0
    tx5 = TX.replace('("SET", 0,', '("SET", 5,').replace('("DIR", 0, 1)', '("DIR", 5, 1)')
    r = simulate_dual(tx5, RX, [(5, 0, 1)])
    assert r.error is None and r.core('RX').cpu.reg[0] == 0x4B, r.error
    # unconnected: RX never sees a falling edge -> timeout with partial state
    r = simulate_dual(tx5, RX, [(0, 0, 1)], max_cycles=300)
    assert r.error and 'TimeoutError' in r.error and 'RX' in r.error


def test_framing_error():
    bad = TX.replace('("SET", 0, 1),     # stop bit', '("SET", 0, 0),     # broken stop')
    r = simulate_dual(bad, RX, STRAIGHT)
    assert r.error and 'expected 1, got 0' in r.error and r.error.startswith('RX'), r.error


def test_contention():
    drive = "program=[('DIR',1,1),('SET',1,1),('WAIT',3),('HALT',)]"
    drive0 = "program=[('DIR',1,1),('WAIT',5),('HALT',)]"
    r = simulate_dual(drive, drive0, STRAIGHT)
    assert r.error and 'contention' in r.error


def test_bidirectional_handshake():
    # TX raises REQ on pin1, RX answers ACK on pin2, TX waits for ACK.
    tx = "program=[('DIR',1,1),('SET',1,1),('WAIT_PIN',2,1,'RISE'),('MOV',3,77),('HALT',)]"
    rx = "program=[('DIR',2,1),('WAIT_PIN',1,1),('SET',2,1),('HALT',)]"
    r = simulate_dual(tx, rx, [(p, p, 0) for p in range(8)])
    assert r.error is None and r.core('TX').cpu.reg[3] == 77, r.error


def test_old_bugs_fixed():
    # edge on first WAIT_PIN sample is detected
    cpu, _ = simulate([("WAIT", 2), ("WAIT_PIN", 1, 0, "FALL"), ("HALT",)], [(2, 1, 0)],
                      60, initial_gpio=[0, 1, 0, 0, 0, 0, 0, 0])
    assert cpu.halted
    # events don't override a pin the CPU drives
    cpu, _ = simulate([("DIR", 0, 1), ("SET", 0, 1), ("WAIT", 5), ("HALT",)], [(3, 0, 0)])
    assert cpu.gpio[0] == 1
    # same-cycle events: last in file wins
    _, ev, _ = parse_program("program=[('HALT',)]\nexternal_events=[(1,2,1),(1,2,0)]")
    cpu, _ = simulate([("WAIT", 3), ("HALT",)], ev)
    assert cpu.gpio[2] == 0
    # parser robustness
    parse_program("program: list\nprogram = [('HALT',)]")
    for src, frag in [("x=1\nprogram=[('MOV',0,x)]", 'must be a literal'),
                      ("program=[('SET',0)]", 'SET syntax'),
                      ("program=[('HALT')]", 'trailing comma')]:
        try:
            parse_program(src)
            raise AssertionError(f'accepted: {src}')
        except ValueError as e:
            assert frag in str(e), (frag, e)
    # invalid initial_gpio is rejected
    try:
        build_core('CPU', "program=[('HALT',)]\ninitial_gpio=[5,0,0,0,0,0,0,0]")
        raise AssertionError('initial_gpio=5 accepted')
    except ValueError as e:
        assert '0 or 1' in str(e)
    # SET without DIR is reported
    r = simulate_single("program=[('SET',4,1),('HALT',)]")
    assert r.error is None and 'GPIO4' in lint(r.cores[0])[0]


def test_timing_consistency():
    # every instruction takes exactly its documented cycles
    cpu, rows = simulate([("MOV", 0, 1), ("WAIT", 0), ("WAIT", 4), ("SHIFT", "L", 0, 3),
                          ("IN", "L", 1, 0), ("DIR", 2, 1), ("JUMP", 1), ("HALT",)])
    assert cpu.cycle == 1 + 0 + 4 + 1 + 1 + 1 + 1 + 1 and cpu.reg[0] == 8
    assert [r['instruction'] for r in rows][:2] == ['MOV 0, 1', 'WAIT 4']


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn(); print('PASS', name)
