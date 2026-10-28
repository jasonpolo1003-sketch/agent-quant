"""Exercise local evidence without any network; emit a durable verification report."""
from pathlib import Path
import hashlib
import os
import json
from datetime import datetime, timezone
import pandas as pd
from data_library.core import Library, parse_csv, with_yoy, select_dates, csv_bytes
from data_library.metadata import SERIES

root = Path(__file__).resolve().parents[1]
lib = Library(os.environ.get('PDL_DATA_DIR', root / 'data'))
report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'series': [], 'offline': True}
for sid in SERIES:
    record = lib.versions(sid)[0]
    raw = (lib.root / record['raw_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record['checksum']
    df = lib.load(sid)
    pd.testing.assert_frame_equal(parse_csv(raw, sid), df, check_dtype=False)
    selected = select_dates(with_yoy(df) if sid == 'CPIAUCSL' else df, '2000-01-01', '2099-12-31')
    exported = pd.read_csv(csv_bytes(selected), parse_dates=['date'])
    pd.testing.assert_frame_equal(selected, exported, check_dtype=False)
    row = {k: record[k] for k in ['id','checksum','rows','observation_start','observation_end','retrieved_at','source_last_modified','source_release_at','download_url','raw_path','clean_path','quality']}
    row['display_rows_from_2000'] = len(selected)
    row['missing_dates'] = df.loc[df.value.isna(), 'date'].dt.strftime('%Y-%m-%d').tolist()
    row['logical_snapshots'] = len(lib.versions(sid))
    row['latest_value'] = float(df.dropna(subset=['value']).iloc[-1].value)
    report['series'].append(row)
cpi = lib.load('CPIAUCSL')
yoy = with_yoy(cpi)
jan99 = cpi.loc[cpi.date == '1999-01-01', 'value'].iloc[0]
jan00 = cpi.loc[cpi.date == '2000-01-01', 'value'].iloc[0]
actual = yoy.loc[yoy.date == '2000-01-01', 'yoy_pct'].iloc[0]
assert abs(actual - (jan00 / jan99 - 1) * 100) < 1e-10
report['cpi_january_2000_check'] = {'january_1999_index': jan99, 'january_2000_index': jan00, 'yoy_pct': actual}
report['data_bytes'] = sum(p.stat().st_size for p in lib.root.rglob('*') if p.is_file())
(root / 'reports').mkdir(exist_ok=True)
(root / 'reports' / 'verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
