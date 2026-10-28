"""Personal Data Library dashboard."""
from datetime import date, datetime, timezone
from pathlib import Path
import os
import pandas as pd
import plotly.graph_objects as go

import streamlit as st
from data_library.core import with_yoy, select_dates, csv_bytes
from data_library.ui_library import UILibrary as Library
from data_library.metadata import SERIES

st.set_page_config(page_title='Personal Data Library', page_icon='📚', layout='wide')
st.markdown('''<style>
.block-container {padding-top: 2.2rem; max-width: 1450px;}
h1 {letter-spacing: -.045em;} h2,h3 {letter-spacing: -.025em;}
[data-testid="stMetric"] {background: #eef5f7; border: 1px solid #dae8ec; border-radius: 12px; padding: 16px;}
[data-testid="stSidebar"] {border-right: 1px solid #dae8ec;}
</style>''', unsafe_allow_html=True)
lib = Library(os.environ.get('PDL_DATA_DIR', str(Path(__file__).parent / 'data')))
st.caption('LOCAL RESEARCH WORKSPACE  /  ECONOMIC DATA')
st.title('Personal Data Library')
st.markdown('Explore the economy. Keep the evidence.')
st.warning('Latest-available history — not point-in-time-safe for backtesting. Values may be revised; observation dates are not publication dates.')

with st.sidebar:
    st.header('Your library')
    page = st.radio('Workspace', ['Economic snapshot', 'Library & explore', 'Research library'])
    st.divider()
    st.subheader('Display window')
    start = st.date_input('From', date(2000, 1, 1), min_value=date(1999, 1, 1), max_value=date.today())
    end = st.date_input('Through', date.today(), min_value=date(1999, 1, 1), max_value=date.today())
    st.caption('Stored history starts January 1999, providing the prior year for CPI YoY from January 2000.')
    search = st.text_input('Search name, topic or source', placeholder='e.g. inflation, BLS, UNRATE')
    topic = st.selectbox('Topic', ['All topics'] + sorted({s['topic'] for s in SERIES.values()}))
    source = st.selectbox('Origin', ['All origins'] + sorted({s['origin'] for s in SERIES.values()}))
    st.divider()
    if st.button('Refresh all datasets', type='primary', width='stretch'):
        with st.spinner('Downloading official FRED snapshots…'):
            st.session_state.refresh_results = [lib.refresh(s) for s in SERIES]
    st.caption('Manual only. No download on startup. Previous successful snapshots are retained if refresh fails.')
    st.caption('Local files · Free sources · No AI')

if start > end:
    st.error('Choose a From date on or before Through.')
    st.stop()
for result in st.session_state.get('refresh_results', []):
    if result['ok']:
        st.success(f"{result['id']}: checked successfully (identical content is deduplicated).")
    else:
        st.error(f"{result['id']}: {result['error']} Previous success, if any, remains available.")

if page == 'Research library':
    from data_library.research_view import render
    render()
    st.stop()

if page == 'Economic snapshot':
    st.subheader('The economic snapshot')
    st.caption('Separate aligned panels; each axis keeps its own definition. CPI inflation uses the seasonally adjusted index.')
    metrics = st.columns(3)

    # Three separate figures preserve readable units, identical selected horizontal ranges.
    for index, sid in enumerate(SERIES):
        records = lib.versions(sid)
        df = lib.load(sid)
        if df.empty:
            st.info(f'{sid}: no local snapshot yet. Use Refresh all datasets or uv run pdl-refresh.')
            continue
        transformed = with_yoy(df) if sid == 'CPIAUCSL' else df
        field = 'yoy_pct' if sid == 'CPIAUCSL' else 'value'
        selected = select_dates(transformed, start, end)
        valid = selected.dropna(subset=[field])
        with metrics[index]:
            if valid.empty:
                st.metric(SERIES[sid]['name'], 'No values')
            else:
                last = valid.iloc[-1]
                st.metric('CPI inflation · YoY' if sid == 'CPIAUCSL' else SERIES[sid]['name'], f'{last[field]:.2f}%')
                st.caption(f"Latest non-null in window: {last.date:%Y-%m}")
        label = ['CPI inflation · year-over-year %', 'Unemployment · % of labor force', 'Effective federal funds rate · %'][index]
        st.markdown(f'#### {label}')
        expanded = selected.set_index('date').reindex(pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(end).replace(day=1), freq='MS'))
        chart = go.Figure(go.Scatter(x=expanded.index, y=expanded[field], mode='lines', connectgaps=False,
            line=dict(color=['#167d9a', '#6954af', '#bf7333'][index], width=2.5), hovertemplate='%{x|%b %Y}: %{y:.2f}%<extra></extra>'))
        chart.update_layout(height=260, margin=dict(l=10,r=15,t=10,b=10), template='plotly_white',
            xaxis=dict(range=[str(start), str(end)]), yaxis_title='Percent', showlegend=False)
        st.plotly_chart(chart, width='stretch', key=sid)
        record = records[0]
        st.caption(f"{sid} · {SERIES[sid]['origin']} via FRED · {SERIES[sid]['adjustment']} · Observation through {record['observation_end']} · Retrieved {record['retrieved_at']} UTC")
        st.markdown(f"[Official source & definitions]({SERIES[sid]['source_url']})")
        if any(record['quality'].values()):
            st.warning(f"{sid}: {record['quality']['missing_values']} null observations; {record['quality']['missing_months']} absent months. Gaps are not filled. CPI YoY may also be null when the prior-year month is unavailable.")
        attempts = lib.attempts(sid)
        if attempts and not attempts[0]['ok']:
            st.error(f"Latest check {attempts[0]['attempted_at']} failed: {attempts[0]['error']}")
else:
    st.subheader('Library & explore')
    catalog = [s for s in lib.catalog(search) if (topic == 'All topics' or s['topic'] == topic) and (source == 'All origins' or s['origin'] == source)]
    st.caption(f'{len(catalog)} of {len(SERIES)} datasets · Search includes names, topics, sources and definitions')
    if not catalog:
        st.info('No datasets match your search and filters.')
        st.stop()
    sid = st.selectbox('Dataset', [s['id'] for s in catalog], format_func=lambda s: f"{SERIES[s]['name']} · {s}")
    meta = SERIES[sid]
    st.markdown(meta['description'])
    st.markdown(f"**Origin:** {meta['origin']}  \n**Distributor:** {meta['distributor']}  \n**Units:** {meta['units']} · **Frequency:** {meta['frequency']} · {meta['adjustment']}")
    st.markdown(f"[Official series, notes & citation]({meta['source_url']}) · [FRED use terms](https://fred.stlouisfed.org/legal/)")
    st.caption(meta['use_notes'])
    if st.button('Refresh this dataset'):
        with st.spinner('Checking official source…'):
            result = lib.refresh(sid)
        if result['ok']:
            st.success('Source checked successfully.')
        else:
            st.error(result['error'])
    records = lib.versions(sid)
    if not records:
        st.info('No successful snapshot saved. Refresh to collect this series.')
        st.stop()
    chosen = st.selectbox('Saved snapshot', range(len(records)), format_func=lambda i: f"{records[i]['retrieved_at']} · {records[i]['checksum'][:12]}")
    record = records[chosen]
    c1,c2,c3 = st.columns(3)
    c1.metric('Latest observation date', record['observation_end'])
    c2.metric('Stored observations', record['rows'])
    c3.metric('Null / absent months', f"{record['quality']['missing_values']} / {record['quality']['missing_months']}")
    st.caption(f"Retrieved at (UTC): {record['retrieved_at']} · Source release time: unknown (not supplied by CSV). HTTP Last-Modified: {record['source_last_modified'] or 'not supplied'} (not a release time).")
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(record['retrieved_at'])).days
    st.caption(f'Snapshot age: {age} days. Manual refresh only; retrieval recency does not guarantee publisher freshness.')
    if any(record['quality'].values()):
        st.warning('Missing observations exist. Nulls and absent months are not zeros; chart lines break at gaps. CPI YoY requires the same month one year earlier.')
    attempts = lib.attempts(sid)
    if attempts:
        latest = attempts[0]
        st.caption(f"Last refresh attempt (UTC): {latest['attempted_at']} · {'success' if latest['ok'] else 'failed'}")
        if not latest['ok']:
            st.error(latest['error'] + ' Showing the retained successful snapshot.')
    df = lib.load(sid, record['checksum'])
    if sid == 'CPIAUCSL':
        df = with_yoy(df)
        st.info('CPI YoY (%) = 100 × (index this month / index in the same calendar month one year earlier − 1). Calculated before display filtering; no row-shift approximation.')
    selected = select_dates(df, start, end)
    if selected.empty:
        st.info('No observations in the selected date window.')
    else:
        field = st.radio('Chart measure', ['value', 'yoy_pct'] if sid == 'CPIAUCSL' else ['value'], format_func=lambda v: 'CPI YoY (%)' if v == 'yoy_pct' else meta['units'], horizontal=True)
        expanded = selected.set_index('date').reindex(pd.date_range(selected.date.min(), selected.date.max(), freq='MS'))
        chart = go.Figure(go.Scatter(x=expanded.index, y=expanded[field], connectgaps=False, line=dict(color='#167d9a', width=2.5)))
        chart.update_layout(height=360, margin=dict(l=15,r=15,t=10,b=15), template='plotly_white', yaxis_title='Percent' if field == 'yoy_pct' else meta['units'], xaxis_title='Observation month')
        st.plotly_chart(chart, width='stretch')
    st.dataframe(selected, hide_index=True, width='stretch')
    st.download_button('Download selected cleaned CSV', data=csv_bytes(selected).getvalue(), file_name=f'{sid}_{start}_{end}.csv', mime='text/csv')
    with st.expander('Snapshot provenance & version history'):
        st.json(record)
        st.caption('Raw response bytes and cleaned Parquet remain versioned separately. SHA-256 deduplication does not overwrite old evidence. Select an older saved snapshot above to inspect revisions.')
        st.dataframe(pd.DataFrame([{k:r[k] for k in ['retrieved_at','checksum','observation_start','observation_end','rows']} for r in records]), hide_index=True)
