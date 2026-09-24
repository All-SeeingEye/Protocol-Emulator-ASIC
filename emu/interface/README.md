# Protocol ISA Waveform Lab

## Launch

```bash
pip install -r requirements.txt
streamlit run app.py
```

Upload `TX.py` or `RX.py`, or edit the sample program in the text box. Click **Run simulation** to view all eight GPIO waveforms, final registers, GPIO direction, and a cycle-by-cycle trace. Download waveforms as PNG and trace as CSV.

**Input format:** define `program` as a literal list of instruction tuples. Optional literal assignments: `external_events = [(cycle, pin, level), ...]`, `initial_gpio = [0, ...]`, `initial_gpio_dir`, and `initial_regs`. The GUI intentionally does **not** execute uploaded Python files; it reads these literal assignments safely. This means dynamic program generation (loops, variables, imports) is not yet supported.

The GUI uses your existing `cpu.py`, `isa.py`, and `simulator.execute()`. Its separate runner resolves WAIT cycle-by-cycle for plotting and applies external events at the beginning of each cycle. `SET` still updates `gpio` directly; pin output and external input are not electrically resolved yet. The GUI runs **one** program at a time; it does not yet run TX and RX concurrently.
