Program Memory
      │
      ▼
 ┌───────────┐
 │    PC     │  ← program counter
 ├───────────┤
 │ R0 ... R3 │  ← general registers
 ├───────────┤
 │ GPIO_OUT  │
 │ GPIO_DIR  │
 ├───────────┤
 │   CYCLE   │  ← protocol time
 └───────────┘

PC          8 bits
R0-R3       8 or 16 bits
GPIO        8 bits
GPIO_DIR    8 bits
cycle       integer
halted      boolean