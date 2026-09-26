# Protocol ISA Waveform Lab

## Launch

```bash
pip install -r requirements.txt
streamlit run app.py
python test_engine.py      # optional: engine self-tests
```

## Modes

**Dual CPU (TX ↔ RX)** (default): upload or edit a transmitter and a receiver program. Both CPUs run in lockstep on one clock and are connected by wires configured in the *Wiring* table (default: TX.GPIOn ↔ RX.GPIOn for all 8 pins, idle level 1 = pull-up). Results appear in three tabs: the wires (colour shows who drives each wire), the TX CPU and the RX CPU. The built-in example sends `0x4B` ('K') over UART on GPIO0; RX ends with `R0 = 0x4B`.

**Single CPU**: run one program, stimulating its input pins with `external_events`.

## Program file format

Only literal assignments are read; uploaded Python is never executed:

- `program = [("DIR", 0, 1), ("SET", 0, 1), ("HALT",), ...]` (required)
- `external_events = [(cycle, pin, level), ...]` sets the level of that pin's wire when no CPU drives it. For events at the same cycle, the later one in the file wins.
- `initial_gpio`, `initial_gpio_dir`, `initial_regs` (8 values each)

## Electrical / timing model

- Each GPIO has an output latch (written by `SET`) and a direction (`DIR`, 0 = input, 1 = output). The latch only reaches the pin while the pin is OUTPUT, so `SET` before `DIR` pre-loads a value glitch-free. Using `SET` on a pin that never becomes OUTPUT is reported as a warning.
- Every cycle: external events are applied, then each wire is resolved from its OUTPUT drivers (none → idle level; two disagreeing → bus contention error), then every running CPU executes one cycle.
- A pin change made by one CPU at cycle *t* is seen by the other at *t+1*.
- `WAIT_PIN` RISE/FALL compare against the previous cycle's level, so an edge on the very first sampled cycle is detected.
- If a simulation fails (timeout, framing error, contention…), the error names the CPU, PC and cycle, and the partial state is still shown.

## Instruction timing

| Instruction | Cycles |
|---|---|
| `SET`, `MOV`, `JUMP`, `HALT`, `IN`, `SHIFT`, `DIR` | 1 |
| `WAIT N` | N (0 allowed) |
| `WAIT_PIN` | 1 per sample until matched |
