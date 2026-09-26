"""Launch with: streamlit run app.py"""
import io
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.patches import Patch

from engine import simulate_single, simulate_dual, lint

HERE = Path(__file__).parent
EXAMPLE_TX = (HERE / 'examples' / 'TX_uart.py').read_text()
EXAMPLE_RX = (HERE / 'examples' / 'RX_uart.py').read_text()

COLORS = {'TX': '#2f6fdf', 'RX': '#e07b24', 'CPU': '#2f6fdf', 'idle': '#b9bec7', 'in': '#b9bec7', 'TX+RX': '#8e44ad'}

st.set_page_config(page_title='Protocol ISA · Waveform Lab', page_icon='〰️', layout='wide')
st.title('Protocol ISA · Waveform Lab')


# ============================================================
# Helpers
# ============================================================

def read_upload(uploaded, fallback):
    if uploaded is None:
        return fallback
    try:
        return uploaded.getvalue().decode('utf-8')
    except UnicodeDecodeError:
        st.error(f'{uploaded.name} is not UTF-8 text.')
        st.stop()


def plot_signals(cycles, signals, end_cycle, legend):
    """Logic-analyzer view. signals: [(label, levels, owners)]; fill colour = who drives."""
    fig, axes = plt.subplots(len(signals), 1, figsize=(15, 0.62 * len(signals) + 1.1),
                             sharex=True, layout='constrained', squeeze=False)
    x = np.append(np.asarray(cycles), end_cycle)
    for ax, (label, levels, owners) in zip(axes[:, 0], signals):
        y = np.append(np.asarray(levels), levels[-1])
        start = 0
        for i in range(1, len(owners) + 1):          # fill each run of the same driver
            if i == len(owners) or owners[i] != owners[start]:
                ax.fill_between(x[start:i + 1], 0, y[start:i + 1], step='post',
                                color=COLORS.get(owners[start], '#999'), alpha=.28, lw=0)
                start = i
        ax.step(x, y, where='post', color='#222', lw=1.4)
        ax.set_yticks([0, 1])
        ax.set_ylim(-0.2, 1.25)
        ax.set_ylabel(label, rotation=0, ha='right', va='center', fontsize=9)
        ax.grid(axis='x', alpha=.25)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    axes[-1, 0].set_xlabel('Simulation cycle')
    axes[-1, 0].set_xlim(0, end_cycle)
    fig.legend(handles=[Patch(color=COLORS[k], alpha=.5, label=v) for k, v in legend.items()],
               loc='outside upper right', ncol=len(legend), frameon=False, fontsize=9)
    return fig


def show_figure(fig, filename, key):
    st.pyplot(fig, width='stretch')
    png = io.BytesIO()
    fig.savefig(png, format='png', dpi=180, bbox_inches='tight')
    plt.close(fig)
    st.download_button('Download waveform PNG', png.getvalue(), filename, 'image/png', key=key)


def changes(levels):
    return len(set(levels)) > 1


def render_cpu(core, end_cycle, hide_idle):
    cpu, df = core.cpu, pd.DataFrame(core.rows)
    tag = core.name.lower()
    c1, c2, c3 = st.columns(3)
    c1.metric('Cycles used', cpu.cycle)
    c2.metric('Final PC', cpu.pc)
    c3.metric('Status', 'HALTED' if cpu.halted else 'STOPPED')
    for note in lint(core):
        st.warning(note)

    st.subheader('GPIO waveforms')
    if df.empty:
        st.warning('No cycles recorded.')
    else:
        signals = []
        for p in range(8):
            levels = df[f'GPIO{p}'].tolist()
            if hide_idle and not changes(levels) and not df[f'DIR{p}'].any():
                continue
            owners = [core.name if d else 'in' for d in df[f'DIR{p}']]
            signals.append((f'GPIO{p}', levels, owners))
        if signals:
            fig = plot_signals(df['cycle'].tolist(), signals, end_cycle,
                               {core.name: 'driven by this CPU (OUTPUT)', 'in': 'INPUT (from wire)'})
            show_figure(fig, f'{tag}_gpio_waveforms.png', f'png_{tag}')
        else:
            st.info('All pins are idle. Untick "Hide idle pins" to show them.')

    left, right = st.columns([3, 2])
    with left:
        st.subheader('Final registers')
        st.dataframe(pd.DataFrame([{
            'Register': f'R{i}', 'Unsigned': v, 'Hex': f'0x{v:08X}', 'Binary': f'{v:032b}',
            'Low byte': chr(v & 0xFF) if 32 <= (v & 0xFF) < 127 else '·'} for i, v in enumerate(cpu.reg)]),
            hide_index=True, width='stretch')
    with right:
        st.subheader('Final GPIO')
        st.dataframe(pd.DataFrame([{
            'Pin': f'GPIO{i}', 'Level': cpu.gpio[i], 'Latch': cpu.gpio_out[i],
            'Direction': 'OUTPUT' if cpu.gpio_dir[i] else 'INPUT'} for i in range(8)]),
            hide_index=True, width='stretch')

    with st.expander('Cycle-by-cycle execution trace'):
        st.dataframe(df, hide_index=True, width='stretch')
        st.download_button('Download cycle trace CSV', df.to_csv(index=False).encode(),
                           f'{tag}_cycle_trace.csv', 'text/csv', key=f'csv_{tag}')
    with st.expander('Recorded SET transitions (output latch)'):
        st.dataframe(pd.DataFrame(cpu.waveform, columns=['cycle', 'pin', 'value']),
                     hide_index=True, width='stretch')


def render_bus(result, hide_idle):
    shared = [n for n in result.nets if n.shared]
    if not shared:
        st.info('No wires connected between TX and RX.')
        return
    df = pd.DataFrame(result.bus_rows)
    if df.empty:
        st.warning('No cycles recorded.')
        return
    signals = []
    for net in shared:
        levels = df[net.name].tolist()
        drivers = df[f'{net.name} driver'].tolist()
        if hide_idle and not changes(levels) and set(drivers) == {'idle'}:
            continue
        signals.append((net.name, levels, drivers))
    if not signals:
        st.info('No wire was driven or changed. Untick "Hide idle pins" to show them.')
        return
    fig = plot_signals(df['cycle'].tolist(), signals, result.cycles,
                       {'TX': 'driven by TX', 'RX': 'driven by RX', 'idle': 'undriven (idle/pull level)'})
    show_figure(fig, 'bus_waveforms.png', 'png_bus')
    with st.expander('Wire trace (level and driver per cycle)'):
        st.dataframe(df, hide_index=True, width='stretch')
        st.download_button('Download wire trace CSV', df.to_csv(index=False).encode(),
                           'bus_trace.csv', 'text/csv', key='csv_bus')


# ============================================================
# Inputs
# ============================================================

with st.sidebar:
    st.header('Setup')
    mode = st.radio('Mode', ['Dual CPU (TX ↔ RX)', 'Single CPU'])
    dual = mode.startswith('Dual')
    max_cycles = st.number_input('Maximum cycles', min_value=1, max_value=100000, value=10000, step=100)
    hide_idle = st.checkbox('Hide idle pins', value=True,
                            help='Hide pins/wires that never change level and are never driven.')
    run_clicked = st.button('Run simulation', type='primary', width='stretch')
    st.caption('Files are read as literal data only (`program`, `external_events`, `initial_gpio`, '
               '`initial_gpio_dir`, `initial_regs`); uploaded Python is never executed.')

if dual:
    st.caption('Two CPUs run in lockstep on one clock. A pin change made by one CPU at cycle t '
               'is seen by the other at cycle t+1.')
    col_tx, col_rx = st.columns(2)
    with col_tx:
        up_tx = st.file_uploader('Transmitter program (TX.py)', type=['py'], key='up_tx')
        tx_source = st.text_area('TX source (editable)', read_upload(up_tx, EXAMPLE_TX), height=360)
    with col_rx:
        up_rx = st.file_uploader('Receiver program (RX.py)', type=['py'], key='up_rx')
        rx_source = st.text_area('RX source (editable)', read_upload(up_rx, EXAMPLE_RX), height=360)

    with st.expander('Wiring between TX and RX', expanded=False):
        st.caption('Each row is one wire. The wire takes the level of whichever CPU has that pin as OUTPUT; '
                   'when neither drives it, it sits at the idle level (pull-up = 1, pull-down = 0). '
                   'Pins not listed are unconnected. `external_events` in a file set the idle level of '
                   "that CPU's wire, which lets you inject stimuli on undriven lines.")
        wiring_df = st.data_editor(
            pd.DataFrame({'TX pin': range(8), 'RX pin': range(8), 'Idle level': [1] * 8}),
            num_rows='dynamic', hide_index=True, key='wiring',
            column_config={
                'TX pin': st.column_config.NumberColumn(min_value=0, max_value=7, step=1, required=True),
                'RX pin': st.column_config.NumberColumn(min_value=0, max_value=7, step=1, required=True),
                'Idle level': st.column_config.NumberColumn(min_value=0, max_value=1, step=1, required=True),
            })
else:
    st.caption('Run one program. Inspect all eight GPIO pins at every simulated cycle and final CPU state. '
               'Use `external_events = [(cycle, pin, value), ...]` to drive input pins.')
    up = st.file_uploader('Upload a program (.py)', type=['py'], key='up_single')
    source = st.text_area('Program source (editable)', read_upload(up, EXAMPLE_TX), height=330)

# ============================================================
# Run
# ============================================================

if run_clicked:
    try:
        if dual:
            wiring = [(int(r['TX pin']), int(r['RX pin']), int(r['Idle level']))
                      for _, r in wiring_df.dropna().iterrows()]
            result = simulate_dual(tx_source, rx_source, wiring, int(max_cycles))
        else:
            result = simulate_single(source, int(max_cycles))
        st.session_state['result'] = (mode, result)
    except Exception as exc:          # parse / setup errors: nothing was simulated
        st.session_state.pop('result', None)
        st.error(f'{type(exc).__name__}: {exc}')
        st.stop()

if 'result' not in st.session_state or st.session_state['result'][0] != mode:
    st.info('Upload programs or use the built-in UART example, then click **Run simulation**.')
    st.stop()

_, result = st.session_state['result']

if result.error:
    st.error(f'Simulation stopped: {result.error}')
    st.caption('The state below is the partial state at the moment the simulation stopped.')

if dual:
    tx, rx = result.core('TX'), result.core('RX')
    m1, m2, m3 = st.columns(3)
    m1.metric('Total cycles', result.cycles)
    m2.metric('TX', 'HALTED' if tx.cpu.halted else 'STOPPED', f'{tx.cpu.cycle} cycles', delta_color='off')
    m3.metric('RX', 'HALTED' if rx.cpu.halted else 'STOPPED', f'{rx.cpu.cycle} cycles', delta_color='off')
    tab_bus, tab_tx, tab_rx = st.tabs(['Wires (TX ↔ RX)', 'TX CPU', 'RX CPU'])
    with tab_bus:
        render_bus(result, hide_idle)
    with tab_tx:
        render_cpu(tx, result.cycles, hide_idle)
    with tab_rx:
        render_cpu(rx, result.cycles, hide_idle)
else:
    render_cpu(result.cores[0], result.cycles, hide_idle)
