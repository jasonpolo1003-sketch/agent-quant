import json,numpy as np,pandas as pd
def cs(h,l):
    b=(np.log(h/l)**2+np.log(h.shift(-1)/l.shift(-1))**2)
    g=np.log(np.maximum(h,h.shift(-1))/np.minimum(l,l.shift(-1)))**2
    k=3-2*np.sqrt(2); a=(np.sqrt(2*b)-np.sqrt(b))/k-np.sqrt(g/k)
    s=2*(np.exp(a)-1)/(1+np.exp(a)); return s.clip(lower=0)
def ar(c,h,l):
    e=(np.log(h)+np.log(l))/2; v=4*(np.log(c)-e)*(np.log(c)-e.shift(-1)); return v
def edge(o,h,l,c):
    o,h,l,c=[np.log(x).values for x in (o,h,l,c)]; m=(h+l)/2
    h1,l1,c1,m1=h[:-1],l[:-1],c[:-1],m[:-1]; o,h,l,c,m=o[1:],h[1:],l[1:],c[1:],m[1:]
    r1=m-o; r2=o-m1; r3=m-c1; r4=c1-m1; r5=o-c1
    tau=(h!=l)|(l!=c1); po1=tau&(o!=h); po2=tau&(o!=l); pc1=tau&(c1!=h1); pc2=tau&(c1!=l1)
    pt=tau.mean(); po=po1.mean()+po2.mean(); pc=pc1.mean()+pc2.mean()
    if pt==0 or po==0 or pc==0: return np.nan
    d1=r1-tau*r5.mean()/pt; d3=r3-tau*r5.mean()/pt; d5=r4-tau*r4.mean()/pt; d7=r2-tau*r2.mean()/pt  # simplified
    x1=-4/po*(r1*r2).mean()-4/pc*(r3*r4).mean()
    x2=-4/po*(r1*r5).mean()-4/pc*(r4*r5).mean()
    e1,e2=(x1+x2)/2,(x1-x2)/2  # simple average form
    s2=e1; return np.sign(s2)*np.sqrt(abs(s2))
eras=[("1993-2000",None,"2001-04-08"),("2001-2007","2001-04-09","2007-12-31"),("2008-2009","2008-01-01","2009-12-31"),("2010-2014","2010-01-01","2014-12-31"),("2015-2019","2015-01-01","2019-12-31"),("2020","2020-01-01","2020-12-31"),("2021-2026","2021-01-01",None)]
rows=[]
for s in ["SPY","QQQ","IWM"]:
    d=pd.DataFrame(json.load(open(f"tiingo/{s}.json"))); d['date']=pd.to_datetime(d['date']).dt.tz_localize(None); d=d.set_index('date')
    for name,a,b in eras:
        x=d.loc[a:b]
        if len(x)<50: continue
        c=cs(x.high,x.low); v=ar(x.close,x.high,x.low)
        rows.append(dict(symbol=s,era=name,days=len(x),cs_bps=round(c.mean()*1e4,2),ar_bps=round(np.sqrt(max(v.mean(),0))*1e4,2),edge_bps=round(edge(x.open,x.high,x.low,x.close)*1e4,2),median_price=round(x.close.median(),1)))
r=pd.DataFrame(rows); r.to_csv("costs/ohlc_spread_estimates.csv",index=False); print(r.to_string())
