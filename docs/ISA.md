1. SET  
   1. assign a value to a pin
   2. SET Px <value>
   3. 1 cycle
2. JUMP
   1. jump to a pc+offset
   2. JUMP <offset>
   3. 1 cycle
3. MOV
   1. move data to Reg a
   2. MOV Ra <value>
   3. 1 cycle
4. HALT
   1. Stop execution
5. WAIT
   1. Wait N number of cycles
   2. WAIT N
   3. N cycle
6. IN
   1. take input from a gpio pin and load it in the register, the register bit and gpio pin index will be the same
   2. IN Rx Px
   3. 1 cycle
7. SHIFT
   1. Shift the register by N to the LEFT or RIGHT
   2. SHIFT R/L Rx N 
   3. 1 cycle
8.  WAIT_PIN
   1.  Don't proceed till the register becomes N
   2.  WAIT_PIN PIN VALUE [MODE] [TIMEOUT]
   3.  INF cycle
9. DIR 
   1. Configure GPIO as in/out/released