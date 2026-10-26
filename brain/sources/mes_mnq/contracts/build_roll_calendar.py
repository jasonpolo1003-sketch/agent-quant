# D-ROLL-01 roll calendar builder. Local R-C files only; no API calls.
import databento as db, pandas as pd, glob, datetime as dt
R='/workspace/data/databento/rc_2026-10-22/'
defs=pd.concat([db.DBNStore.from_file(f).to_df() for f in sorted(glob.glob(R+'def_years/*.dbn.zst'))])
defs=defs[defs.raw_symbol.str.fullmatch(r'M(ES|NQ)[HMUZ]\d')]
defs['root']=defs.raw_symbol.str[:3]
d=defs.sort_index().groupby(['instrument_id']).last().reset_index()
d['exp']=pd.to_datetime(d.expiration).dt.tz_convert('America/New_York').dt.date
d=d.sort_values(['root','exp'])
m=db.DBNStore.from_file(R+'glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-20261022.dbn.zst').to_df()
m=m[m.instrument_id.isin(d.instrument_id)]
et=m.index.tz_convert('America/New_York')
m['td']=(et+pd.Timedelta(hours=6)).date  # CME trade date: session opens 18:00 ET prior day
vol=m.groupby(['td','instrument_id']).volume.sum()
tds=sorted(set(m.td))
rows=[]
for root,g in d.groupby('root'):
    g=g.reset_index(drop=True)
    for i in range(len(g)-1):
        a,b=g.iloc[i],g.iloc[i+1]
        r=a.exp-dt.timedelta(days=8)
        while r.weekday()>=5 or (tds[0]<r<=tds[-1] and r not in set(tds)): r-=dt.timedelta(days=1)
        if r<dt.date(2019,5,1): continue
        agree=None
        if tds[0]<r<=tds[-1]:
            p=max(t for t in tds if t<r)
            va=vol.get((p,a.instrument_id),0); vb=vol.get((p,b.instrument_id),0)
            # first prior-day-volume roll date
            vr=next((t for t in tds if t>a.exp-dt.timedelta(days=30) and vol.get((max(x for x in tds if x<t),b.instrument_id),0)>vol.get((max(x for x in tds if x<t),a.instrument_id),0)),None)
            agree=dict(prev_td=p,from_vol_prev=va,to_vol_prev=vb,to_already_larger=vb>va,volume_roll_date=vr,days_diff=(None if vr is None else sum(1 for t in tds if min(r,vr)<=t<max(r,vr))*(1 if vr>r else -1)))
        rows.append(dict(root=root,roll_trade_date=r,from_contract=a.raw_symbol,to_contract=b.raw_symbol,from_expiration=a.exp,to_instrument_id=b.instrument_id,**(agree or {})))
o=pd.DataFrame(rows)
o[['root','roll_trade_date','from_contract','to_contract','from_expiration','to_instrument_id']].to_csv('/workspace/mes_mnq/contracts/roll_calendar_2019_2026.csv',index=False)
o.to_csv('/workspace/mes_mnq/contracts/roll_volume_check.csv',index=False)
print(o.to_string())
