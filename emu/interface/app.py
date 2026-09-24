"""Launch with: streamlit run app.py"""
import io
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from engine import parse_program, simulate

st.set_page_config(page_title='Protocol ISA · Waveform Lab', page_icon='〰️', layout='wide')
st.title('Protocol ISA · Waveform Lab')
st.caption('Load one TX.py or RX.py program. Inspect all eight GPIO pins at every simulated cycle and final CPU state.')

example = '''# Only literal assignments are read; uploaded Python is never executed.
program = [
    ("DIR", 0, 1),
    ("SET", 0, 1),     # UART idle
    ("SET", 0, 0),     # start
    ("WAIT", 9),
    ("SET", 0, 1),     # data bit 0 of 0x55
    ("WAIT", 9),
    ("SET", 0, 0),
    ("WAIT", 9),
    ("SET", 0, 1),
    ("WAIT", 9),
    ("SET", 0, 0),
    ("WAIT", 9),
    ("SET", 0, 1),
    ("WAIT", 9),
    ("SET", 0, 0),
    ("WAIT", 9),
    ("SET", 0, 1),
    ("WAIT", 9),
    ("SET", 0, 0),
    ("WAIT", 9),
    ("SET", 0, 1),     # stop
    ("WAIT", 9),
    ("HALT",),
]
'''
with st.sidebar:
    st.header('Program')
    uploaded = st.file_uploader('Upload TX.py or RX.py', type=['py'])
    max_cycles = st.number_input('Maximum cycles', min_value=1, max_value=100000, value=10000, step=100)
    st.info('For RX input stimuli, include external_events = [(cycle, pin, value), ...] in your file. Pin changes are applied at the start of the specified cycle.')
    run_clicked = st.button('Run simulation', type='primary', width="stretch")
source = uploaded.getvalue().decode('utf-8') if uploaded else example
source = st.text_area('Program source (editable)', value=source, height=330)
if run_clicked:
    try:
        program, events, initial = parse_program(source)
        cpu, rows = simulate(program, events, int(max_cycles),
            initial_gpio=initial.get('initial_gpio'),
            initial_gpio_dir=initial.get('initial_gpio_dir'),
            initial_regs=initial.get('initial_regs'))
        st.session_state['result'] = (cpu, rows)
    except Exception as exc:
        st.error(f'{type(exc).__name__}: {exc}')
        st.stop()
if 'result' not in st.session_state:
    st.info('Upload a program or use the built-in UART TX example, then click Run simulation.')
    st.stop()
cpu, rows = st.session_state['result']
df = pd.DataFrame(rows)
col1, col2, col3 = st.columns(3)
col1.metric('Cycles elapsed', cpu.cycle)
col2.metric('Final PC', cpu.pc)
col3.metric('Status', 'HALTED' if cpu.halted else 'RUNNING')
st.subheader('GPIO waveforms')
if df.empty:
    st.warning('No cycles recorded.')
else:
    fig, axes = plt.subplots(8, 1, figsize=(15, 9), sharex=True, layout='constrained')
    for pin, ax in enumerate(axes):
        levels = df[f'GPIO{pin}'].tolist()
        times = df['cycle'].tolist()
        ax.step(times + [cpu.cycle], levels + [levels[-1]], where='post', linewidth=1.8)
        ax.set_yticks([0, 1])
        ax.set_ylim(-0.25, 1.25)
        ax.set_ylabel(f'GPIO{pin}', rotation=0, labelpad=32)
        ax.grid(axis='x', alpha=.3)
    axes[-1].set_xlabel('Simulation cycle')
    st.pyplot(fig, width="stretch")
    png = io.BytesIO()
    fig.savefig(png, format='png', dpi=180, bbox_inches='tight')
    st.download_button('Download waveform PNG', data=png.getvalue(), file_name='gpio_waveforms.png', mime='image/png')
    plt.close(fig)
st.subheader('Final registers')
reg_df = pd.DataFrame([{'Register': f'R{i}', 'Unsigned': val, 'Hex': f'0x{val:08X}', 'Binary': f'{val:032b}'} for i, val in enumerate(cpu.reg)])
st.dataframe(reg_df, hide_index=True, width="stretch")
st.subheader('Final GPIO and direction')
gpio_df = pd.DataFrame([{'Pin': f'GPIO{i}', 'Level': cpu.gpio[i], 'Direction': 'OUTPUT' if cpu.gpio_dir[i] else 'INPUT'} for i in range(8)])
st.dataframe(gpio_df, hide_index=True, width="stretch")
with st.expander('Cycle-by-cycle execution trace'):
    st.dataframe(df, hide_index=True, width="stretch")
    st.download_button('Download cycle trace CSV', df.to_csv(index=False).encode(), 'cycle_trace.csv', 'text/csv')
with st.expander('Recorded SET transitions'):
    st.dataframe(pd.DataFrame(cpu.waveform, columns=['cycle','pin','value']), hide_index=True, width="stretch")
