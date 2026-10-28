import pandas as pd
import pytest
from data_library import core


def test_parse_official_csv_preserves_null_and_history():
    df = core.parse_csv(b'observation_date,CPIAUCSL\n1998-12-01,100\n1999-01-01,101\n1999-02-01,.\n', 'CPIAUCSL')
    assert list(df.date.dt.strftime('%Y-%m-%d')) == ['1999-01-01', '1999-02-01']
    assert df.value.iloc[0] == 101
    assert pd.isna(df.value.iloc[1])


@pytest.mark.parametrize('rows', [
    '1999-01-01,1\n1999-01-01,2', 'not-a-date,1',
    '1999-01-02,1', '1999-01-01,nope', '1999-01-01,inf',
    ',1', '1998-01-01,1', '1999-01-01,.',
])
def test_reject_invalid_imports(rows):
    with pytest.raises(ValueError):
        core.parse_csv(('observation_date,CPIAUCSL\n' + rows + '\n').encode(), 'CPIAUCSL')


def test_calendar_yoy_and_gap_detection_not_row_shift():
    df = core.parse_csv(b'observation_date,CPIAUCSL\n1999-01-01,100\n1999-03-01,0\n2000-01-01,110\n2000-02-01,120\n2000-03-01,10\n', 'CPIAUCSL')
    out = core.with_yoy(df)
    assert out.loc[out.date == '2000-01-01', 'yoy_pct'].iloc[0] == pytest.approx(10)
    assert pd.isna(out.loc[out.date == '2000-02-01', 'yoy_pct'].iloc[0])
    assert pd.isna(out.loc[out.date == '2000-03-01', 'yoy_pct'].iloc[0])
    assert core.quality(df) == {'missing_values': 0, 'missing_months': 10}
    selected = core.select_dates(out, '2000-01-01', '2000-02-01')
    assert len(selected) == 2
    assert list(pd.read_csv(core.csv_bytes(selected)).columns) == ['date', 'value', 'yoy_pct']
