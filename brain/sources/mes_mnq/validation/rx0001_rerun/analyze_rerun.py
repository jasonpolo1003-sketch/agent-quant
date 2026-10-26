import pickle,json,math,itertools,sys
import numpy as np,pandas as pd
from scipy.cluster.hierarchy import linkage,fcluster
from scipy.spatial.distance import squareform
from scipy.stats import norm
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples
sys.path.insert(0,'src'); from quant_brain.backtest import stats
S=pickle.load(open('out/streams.pkl','rb')); O={}
cfgs=sorted(set(c for c,p in S)); rules=sorted(set(c.rsplit('|',2)[0] for c in cfgs)); assert len(rules)==24
arms=[(f,c) for f in ['next_open','same_close'] for c in [0,2,5,10]]
for per in ['IS','OOS','FULL']:
  df=pd.concat({f'{r}|{f}|{c}bps':S[(f'{r}|{f}|{c}bps',per)] for r in rules for f,c in arms},axis=1)
  df.index.name='date'; df.to_csv(f'res/daily_returns_{per}.csv.gz',float_format='%.8g')
def dist(C): return np.sqrt(np.clip(0.5*(1-C),0,None))
def eig(C):
  ev=np.clip(np.linalg.eigvalsh(C),0,None); n=len(ev)
  return {'nyholt':float(1+(n-1)*(1-np.var(ev,ddof=1)/n)),'li_ji':float(sum((e>=1)+(e-math.floor(e)) for e in ev))}
def hier(C,cuts):
  L=linkage(squareform(dist(C),checks=False),'average'); return {str(t):int(len(set(fcluster(L,t,'distance')))) for t in cuts}
def onc(C,seeds=20):
  X=dist(C); best=(-1e9,None,None)
  for k in range(2,len(C)):
    for s in range(seeds):
      lab=KMeans(k,n_init=1,random_state=s).fit_predict(X)
      if len(set(lab))<2: continue
      sil=silhouette_samples(X,lab); q=sil.mean()/(sil.std()+1e-12)
      if q>best[0]: best=(q,k,lab)
  return best
cuts=[0.1,0.2,0.3,0.4,0.5]
O['cutoff_to_rho']={str(t):1-2*t*t for t in cuts}
for per in ['FULL','OOS','IS']:
  df=pd.concat({r:S[(f'{r}|next_open|5bps',per)] for r in rules},axis=1).dropna()
  C=df.corr().to_numpy(); q,k,lab=onc(C)
  O[per]={'base_arm':'next_open|5bps','T':len(df),'mean_offdiag_rho':float(C[~np.eye(24,dtype=bool)].mean()),'min_rho':float(C.min()),
    'eigen':eig(C),'hier_avg_clusters':hier(C,cuts),'onc_k':int(k),'onc_quality':float(q),'onc_labels':dict(zip(rules,map(int,lab)))}
  if per=='FULL': pd.DataFrame(C,index=rules,columns=rules).to_csv('res/corr_24_FULL_next_open_5bps.csv',float_format='%.4f')
  d2=pd.concat({c:S[(c,per)] for c in cfgs},axis=1).dropna(); C2=d2.corr().to_numpy()
  O[per]['all192']={'eigen':eig(C2),'hier_avg_clusters':hier(C2,cuts),'min_rho_within_rule_across_arms':float(min(d2[[c for c in cfgs if c.startswith(r+'|')]].corr().to_numpy().min() for r in rules))}
oos={c:S[(c,'OOS')] for c in cfgs}; srs={c:stats.sharpe_per_period(v) for c,v in oos.items()}
g=stats.EULER_GAMMA
def dsr(x,V,N):
  x=np.asarray(x,float); sr=stats.sharpe_per_period(x); sk,ku=stats._biased_moments(x); T=len(x)
  z=math.sqrt(V)*((1-g)*norm.ppf(1-1/N)+g*norm.ppf(1-1/(N*math.e))) if N>1 else 0.0
  return float(norm.cdf((sr-z)*math.sqrt(T-1)/math.sqrt(1-sk*sr+(ku-1)/4*sr*sr))),z
V192=float(np.var(list(srs.values()),ddof=1)); V24=float(np.var([srs[f'{r}|next_open|5bps'] for r in rules],ddof=1))
best=max(cfgs,key=lambda c: dsr(oos[c],V192,192)[0])
lab=O['OOS']['onc_labels']; dfb=pd.concat({r:oos[f'{r}|next_open|5bps'] for r in rules},axis=1).dropna()
def Vclus(labels):
  grp={};[grp.setdefault(v,[]).append(r) for r,v in labels.items()]
  return float(np.var([stats.sharpe_per_period(dfb[m].mean(1)) for m in grp.values()],ddof=1)) if len(grp)>1 else 0.0
Ncands=sorted(set([O['OOS']['onc_k'],round(O['OOS']['eigen']['li_ji'])]+list(O['OOS']['hier_avg_clusters'].values())+list(O['FULL']['hier_avg_clusters'].values())+[O['FULL']['onc_k'],24,192,278]))
O['dsr']={'best_config':best,'sr':srs[best],'V_192':V192,'V_24_base':V24,'V_onc_clusters':Vclus(lab),'by_N':{}}
for N in Ncands:
  O['dsr']['by_N'][str(N)]={'V192':dsr(oos[best],V192,N)[0],'V24':dsr(oos[best],V24,N)[0]}
O['dsr']['onc_cluster_V']={'N':O['OOS']['onc_k'],'dsr':dsr(oos[best],Vclus(lab),O['OOS']['onc_k'])[0]}
nb=f"{best.rsplit('|',2)[0]}|next_open|5bps"; O['dsr']['base_arm_of_best']={'config':nb,'by_N':{str(N):dsr(oos[nb],V24,N)[0] for N in Ncands}}
def cscv(M,S_=16):
  T,N=M.shape; bl=np.array_split(np.arange(T),S_); lam=[]
  sh=lambda X:(lambda m,s:np.where(s>0,m/s,0))(X.mean(0),X.std(0,ddof=1))
  for comb in itertools.combinations(range(S_),S_//2):
    i=np.concatenate([bl[j] for j in comb]); o=np.concatenate([bl[j] for j in range(S_) if j not in comb])
    si,so=sh(M[i]),sh(M[o]); b=int(np.argmax(si)); w=((so<so[b]).sum()+1)/(N+1); lam.append(math.log(w/(1-w)))
  return float((np.array(lam)<=0).mean())
O['pbo']={}
for f,c in arms:
  M=pd.concat({r:S[(f'{r}|{f}|{c}bps','FULL')] for r in rules},axis=1).dropna().to_numpy()
  O['pbo'][f'{f}|{c}bps']={str(s):cscv(M,s) for s in [8,12,16]}
M=pd.concat({c:S[(c,'FULL')] for c in cfgs},axis=1).dropna().to_numpy(); O['pbo']['all192_S16']=cscv(M,16)
json.dump(O,open('res/rerun_results.json','w'),indent=1)
print(json.dumps({k:(v if k not in('OOS','FULL','IS') else {kk:vv for kk,vv in v.items() if kk!='onc_labels'}) for k,v in O.items()},indent=1))
