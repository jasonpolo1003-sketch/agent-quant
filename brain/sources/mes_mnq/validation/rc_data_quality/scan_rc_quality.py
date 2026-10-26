"""Local data-quality scan of Databento R-C (GLBX.MDP3 MES/MNQ). No API calls. status: unreviewed"""
import databento as db, glob, pandas as pd, numpy as np, json, os, warnings
warnings.filterwarnings('ignore')
R='/workspace/data/databento/rc_2026-10-22/'; O=os.path.dirname(os.path.abspath(__file__))+'/'
CK=O+'checkpoint.json'; ck=json.load(open(CK)) if os.path.exists(CK) else {}
def save(): json.dump(ck,open(CK,'w'),indent=1,default=str)
ld=lambda f: db.DBNStore.from_file(R+f).to_df()
# definitions
d=pd.concat([db.DBNStore.from_file(f).to_df().reset_index() for f in sorted(glob.glob(R+'def_years/*.dbn.zst'))])
fut=d[d.instrument_class=='F'].sort_values('ts_recv').drop_duplicates('instrument_id',keep='last')
fut['root']=fut.raw_symbol.str[:3]
dd=fut[['instrument_id','raw_symbol','root','expiration','min_price_increment','contract_multiplier','unit_of_measure_qty','min_price_increment_amount']]
dd.to_csv(O+'definitions_outrights.csv',index=False)
defs={'n_records':len(d),'n_outright_ids':len(fut),
 'tick_sizes':fut.groupby('root').min_price_increment.unique().apply(list).to_dict(),
 'uom_qty':fut.groupby('root').unit_of_measure_qty.unique().apply(list).to_dict(),
 'tick_value':fut.groupby('root').min_price_increment_amount.unique().apply(list).to_dict(),
 'n_contracts':fut.groupby('root').raw_symbol.nunique().to_dict(),
 'dup_symbol_ids':int(fut.raw_symbol.duplicated().sum())}
exp=fut.expiration.dt.tz_convert('America/New_York')
defs['expiry_not_3rd_friday']=fut[~((exp.dt.weekday==4)&(exp.dt.day.between(15,21)))].raw_symbol.tolist()
ck['defs']=defs; save(); print(defs)
id2={r.instrument_id:r for r in dd.itertuples()}
# 1m
m=ld('glbx-mdp3_ohlcv-1m_MES-MNQ-FUT_20190501-20261022.dbn.zst').reset_index()
m=m[~m.symbol.str.contains('-')].copy(); m['root']=m.symbol.str[:3]
ck['n_1m_outright']=len(m); ck['unmapped_ids']=int((~m.instrument_id.isin(id2)).sum())
flags=[]
def F(name,mask,df): 
    x=df[mask].copy(); x['flag']=name; flags.append(x); ck.setdefault('counts',{})[name]=int(mask.sum())
F('nonpositive',(m[['open','high','low','close']]<=0).any(axis=1),m)
F('high_lt_low',m.high<m.low,m)
F('oc_outside_hl',(m[['open','close']].max(axis=1)>m.high+1e-9)|(m[['open','close']].min(axis=1)<m.low-1e-9),m)
off=lambda s: (np.abs(s*4-np.round(s*4))>1e-6)
F('off_tick',off(m.open)|off(m.high)|off(m.low)|off(m.close),m)
F('zero_volume',m.volume==0,m)
F('dup_ts',m.duplicated(['instrument_id','ts_event'],keep=False),m)
# trade date (CME): CT time; >=17:00 belongs to next day
ct=m.ts_event.dt.tz_convert('America/Chicago'); m['ct']=ct
m['tdate']=(ct+pd.Timedelta(hours=7)).dt.date
F('in_daily_break',ct.dt.hour==16,m)
# front month = highest volume per root/tdate
vol=m.groupby(['root','tdate','symbol']).volume.sum().reset_index()
front=vol.sort_values('volume').drop_duplicates(['root','tdate'],keep='last')
front.to_csv(O+'front_by_volume.csv',index=False)
fm=m.merge(front[['root','tdate','symbol']],on=['root','tdate','symbol']).sort_values(['root','ts_event'])
# jumps on front month (same contract consecutive bars)
g=fm.groupby('symbol')
fm['ret']=g.close.pct_change(); fm['gapmin']=g.ts_event.diff().dt.total_seconds()/60
fm['rng']=(fm.high-fm.low)/fm.close
fm['medrng']=g.rng.transform(lambda s:s.rolling(390,min_periods=60).median())
fm['barmove']=np.maximum((fm.high-fm.low)/fm.close,fm.ret.abs())
j=(fm.ret.abs()>0.01)|(fm.rng>0.02)|((fm.barmove>25*fm.medrng)&(fm.barmove>0.004))
F('front_jump',j,fm)
F('front_jump_gt5pct',(fm.ret.abs()>0.05)|(fm.rng>0.05),fm)
# volume anomalies: front-month daily volume vs 20d median
fv=front.copy(); fv['med20']=fv.groupby('root').volume.transform(lambda s:s.rolling(20,min_periods=5).median())
fv['ratio']=fv.volume/fv.med20
va=fv[(fv.ratio<0.2)|(fv.ratio>5)]; va.to_csv(O+'flag_volume_anomaly_days.csv',index=False); ck['counts']['volume_anomaly_days']=len(va)
# missing minutes front month per tdate; expected 17:00 prev->16:00 = 1380
cov=fm.groupby(['root','tdate']).agg(n=('ts_event','size'),first=('ct','min'),last=('ct','max'),vol=('volume','sum')).reset_index()
cov['missing_vs_1380']=1380-cov.n
# longest internal gap
fm['gap_prev']=fm.groupby(['root','tdate']).ts_event.diff().dt.total_seconds()/60-1
lg=fm.groupby(['root','tdate']).gap_prev.max().rename('longest_gap_min')
gi=fm.loc[fm.groupby(['root','tdate']).gap_prev.idxmax().dropna()].set_index(['root','tdate']).ct.rename('gap_end_ct')
cov=cov.join(lg,on=['root','tdate']).join(gi,on=['root','tdate'])
cov.to_csv(O+'front_coverage_by_day.csv',index=False)
cov[(cov.missing_vs_1380>30)|(cov.longest_gap_min>=5)].to_csv(O+'flag_front_coverage_days.csv',index=False)
ck['coverage']={'days':len(cov),'median_missing':float(cov.missing_vs_1380.median()),
 'days_missing_gt30':int((cov.missing_vs_1380>30).sum()),'days_gap_ge5':int((cov.longest_gap_min>=5).sum()),
 'days_full_1380':int((cov.n>=1380).sum()),'total_missing_front':int(cov.missing_vs_1380.clip(lower=0).sum())}
# RTH subset 8:30-15:00 CT
rth=fm[(fm.ct.dt.hour*60+fm.ct.dt.minute).between(510,899)]
rc=rth.groupby(['root','tdate']).size(); ck['rth']={'days':len(rc),'days_full_390':int((rc==390).sum()),'days_lt_380':int((rc<380).sum()),'median':float(rc.median())}
rc[rc<390].rename('rth_bars').to_csv(O+'flag_rth_incomplete_days.csv')
# missing weekdays
alld=pd.bdate_range('2019-05-06','2026-10-21').date
for r in ['MES','MNQ']:
    have=set(cov[cov.root==r].tdate); ck.setdefault('missing_weekdays',{})[r]=[str(x) for x in alld if x not in have]
# outage Nov 2025
w=m[(m.ts_event>='2025-11-27 12:00Z')&(m.ts_event<'2025-11-29 00:00Z')&(m.root=='MES')]
ts=np.sort(w.ts_event.unique()); gaps=pd.Series(ts[1:]-ts[:-1],index=ts[:-1])
big=gaps[gaps>pd.Timedelta('30min')]
ck['outage_nov2025']=[{'from_utc':str(k),'to_utc':str(k+v),'hours':v.total_seconds()/3600} for k,v in big.items()]
# 1m->daily vs ohlcv-1d (UTC day), front month
dly=ld('glbx-mdp3_ohlcv-1d_MES-MNQ-FUT_20190501-20261022.dbn.zst').reset_index()
dly=dly[~dly.symbol.str.contains('-')]; dly['udate']=dly.ts_event.dt.date
m['udate']=m.ts_event.dt.date
agg=m.groupby(['symbol','udate']).agg(o=('open','first'),h=('high','max'),l=('low','min'),c=('close','last'),v=('volume','sum')).reset_index()
uf=agg.sort_values('v').assign(root=lambda x:x.symbol.str[:3]).drop_duplicates(['root','udate'],keep='last')
cmp=uf.merge(dly,on=['symbol','udate'],how='left')
cmp['dh']=cmp.h-cmp.high; cmp['dl']=cmp.l-cmp.low; cmp['do']=cmp.o-cmp.open; cmp['dc']=cmp.c-cmp.close; cmp['dv']=cmp.v.astype('int64')-cmp.volume.astype('float')
bad=cmp[(cmp.high.isna())|(cmp[['dh','dl','do','dc']].abs().max(axis=1)>0)|(cmp.dv.abs()>0)]
bad.to_csv(O+'flag_daily_mismatch.csv',index=False)
ck['daily_cmp']={'front_days':len(cmp),'mismatch_rows':len(bad),'missing_in_1d':int(cmp.high.isna().sum()),
 'ohlc_mismatch':int((cmp[['dh','dl','do','dc']].abs().max(axis=1)>0).sum()),'vol_mismatch':int((cmp.dv.abs()>0).sum())}
# daily-only vs 1m volume totals overall
ck['vol_total_1m']=int(m.volume.sum()); ck['vol_total_1d']=int(dly.volume.sum())
# statistics: light check (settlement count) - skip if memory heavy
cols=['ts_event','symbol','root','open','high','low','close','volume','flag']
for nm in set(x.flag.iloc[0] for x in flags if len(x)):
    pd.concat([x for x in flags if len(x) and x.flag.iloc[0]==nm])[[c for c in cols if c in flags[0].columns or c=='flag']].to_csv(O+f'flag_{nm}.csv',index=False)
jj=pd.concat([x for x in flags if len(x) and x.flag.iloc[0]=='front_jump']) if ck['counts']['front_jump'] else None
if jj is not None:
    jj['ct']=jj.ts_event.dt.tz_convert('America/Chicago'); jj[['ct','symbol','open','high','low','close','volume','ret','rng','medrng']].sort_values('rng',ascending=False).to_csv(O+'flag_front_jump.csv',index=False)
ck['done']=True; save(); print(json.dumps(ck,indent=1,default=str)[:6000])
