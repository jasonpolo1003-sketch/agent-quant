"""Fixed first-release catalog; FRED distributes rather than originates these data."""
SERIES = {
    'CPIAUCSL': dict(name='Consumer Price Index', topic='Inflation', origin='U.S. Bureau of Labor Statistics', units='Index 1982–1984=100', adjustment='Seasonally adjusted', description='Monthly prices paid by urban consumers for a representative basket. The index is not an inflation percentage.'),
    'UNRATE': dict(name='Unemployment rate', topic='Labor', origin='U.S. Bureau of Labor Statistics', units='Percent', adjustment='Seasonally adjusted', description='Unemployed people as a percentage of the civilian labor force, age 16 and older.'),
    'FEDFUNDS': dict(name='Effective federal funds rate', topic='Interest rates', origin='Board of Governors of the Federal Reserve System (US)', units='Percent', adjustment='Not seasonally adjusted', description='Monthly effective federal funds rate. This is not the FOMC target range.'),
}
for series_id, metadata in SERIES.items():
    metadata.update(id=series_id, distributor='Federal Reserve Bank of St. Louis (FRED)', frequency='Monthly', source_url=f'https://fred.stlouisfed.org/series/{series_id}', use_notes='Check series-specific source/copyright notes and FRED terms before reuse or redistribution: https://fred.stlouisfed.org/legal/. Latest-available history, not point-in-time-safe backtest evidence.')
