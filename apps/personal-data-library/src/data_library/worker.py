"""Bounded reconciliation. Notes never grant network or execution permissions."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import tomllib
from .intake_store import IntakeStore
from .intake_scan import scan
from .intake_process import drain
from .locking import lock, Busy
from .obsidian_status import publish_status, atomic_write

PROJECT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    path = Path(path or os.environ.get('PDL_INTAKE_CONFIG', PROJECT/'config/intake.toml'))
    if not path.exists():
        raise ValueError('No local intake config. Copy config/intake.example.toml to config/intake.toml and opt in explicit folders.')
    config = tomllib.loads(path.read_text(encoding='utf-8'))
    config.setdefault('data_dir', os.environ.get('PDL_DATA_DIR', str(PROJECT/'data')))
    inbox, output = Path(config['inbox']).resolve(), Path(config['output']).resolve()
    if inbox == output.parent or inbox in output.parents or output.parent in inbox.parents:
        raise ValueError('Generated output must be outside the input root')
    if int(config.get('max_files',100)) not in range(1,101):
        raise ValueError('max_files must be 1..100')
    return config


def fred_subprocess(sid, seconds, root):
    from .metadata import SERIES
    if sid not in SERIES:
        raise ValueError('Series not allowlisted')
    try:
        proc = subprocess.run([sys.executable,'-m','data_library.worker','_fred',sid], cwd=PROJECT,
                              capture_output=True,text=True,timeout=seconds,env={**os.environ,'PDL_DATA_DIR':str(root)})
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        if proc.returncode:
            return {'id':sid,'ok':False,'error':proc.stderr[-1000:] or f'Child exit {proc.returncode}'}
        raise ValueError('Empty child refresh response')
    except (subprocess.TimeoutExpired, ValueError) as exc:
        return {'id':sid,'ok':False,'error':f'Bounded FRED fetch failed: {exc}'}


def refresh_due(store, deadline, refresher=None):
    from .metadata import SERIES
    state = store.state('fred_due') or {'sources':{}}
    now=time.time()
    results=[]
    for sid in SERIES:
        source=state['sources'].get(sid,{})
        day=time.strftime('%Y-%m-%d',time.gmtime())
        if source.get('day') != day:
            source.update(day=day, attempts=0)
        if source.get('next_due',0)>now or source.get('next_retry',0)>now or source.get('attempts',0)>=3:
            continue
        remaining=deadline-time.monotonic()
        if remaining<2: break
        # Persist attempt reservation before network, including abrupt worker death.
        source['attempts']=source.get('attempts',0)+1
        source['next_retry']=now+300*(2**(source['attempts']-1))
        state['sources'][sid]=source
        store.state('fred_due',state)
        if refresher:
            result=refresher(sid)
        else:
            result=fred_subprocess(sid,min(25,remaining-1),store.root)
        source['result']=result
        if result['ok']:
            source.update(last_success=now,next_due=now+86400,next_retry=0)
        results.append(result)
        state['sources'][sid]=source
        successes=[v.get('last_success') for v in state['sources'].values()]
        state['last_success']=min(successes) if len(successes)==len(SERIES) and all(successes) else None
        retries=[v['next_retry'] for v in state['sources'].values() if v.get('next_retry')]
        state['next_retry']=min(retries) if retries else None
        store.state('fred_due',state)
        store.event('fred_refresh',json.dumps(result))
    return results


def run_once(config, notes_only=False, refresher=None):
    root=Path(config['data_dir'])
    started=time.monotonic()
    deadline=started+min(float(config.get('max_seconds',90)),90)
    try:
        with lock(root,'worker',timeout=0):
            store=IntakeStore(root)
            if store.state('paused'):
                return {'status':'paused'}
            result={'status':'ok', **scan(store,config['inbox'],stability=config.get('stability_seconds',1),cap=config.get('max_files',100))}
            result.update(drain(store,config['inbox'],cap=config.get('max_files',100),deadline=deadline))
            if config.get('quant_manifest') and config.get('quant_root'):
                from .quant_catalog import update
                entries=json.loads(Path(config['quant_manifest']).read_text(encoding='utf-8'))
                result['quant']=update(store,config['quant_root'],entries)
            if config.get('refresh_fred',False) and not notes_only:
                result['fred']=refresh_due(store,deadline,refresher)
            result['feedback']=publish_status(store,config['output'])
            result['elapsed_seconds']=round(time.monotonic()-started,3)
            result['at']=time.time()
            store.state('last_run',result)
            atomic_write(root/'research/exports/last-run.json',json.dumps(result,indent=2).encode())
            return result
    except Busy as exc:
        return {'status':'busy','recovery':str(exc)}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0]=='_fred':
        from .core import Library
        from .fred import fetch
        sid=argv[1]
        # Fetch first: constructor/schema access only occurs once the network completes.
        from .metadata import SERIES
        if sid not in SERIES: raise ValueError('Series not allowed')
        raw,url,modified=fetch(sid)
        root=os.environ.get('PDL_DATA_DIR',str(PROJECT/'data'))
        result=Library(root).refresh(sid,lambda _: (raw,url,modified))
        print(json.dumps(result))
        return int(not result['ok'])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config')
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('scan');p.add_argument('--dry-run',action='store_true')
    p=commands.add_parser('run-once');p.add_argument('--notes-only',action='store_true')
    commands.add_parser('status')
    p=commands.add_parser('retry');p.add_argument('item')
    commands.add_parser('pause');commands.add_parser('resume')
    p=commands.add_parser('schedule');p.add_argument('action',choices=['status','enable','disable']);p.add_argument('--confirm-activation',action='store_true')
    args=parser.parse_args(argv)
    if args.command=='schedule':
        from .scheduling import status, enable, disable
        result=enable(confirmed=args.confirm_activation) if args.action=='enable' else disable() if args.action=='disable' else status()
    else:
        config=load_config(args.config)
        store=IntakeStore(config['data_dir'])
        if args.command=='scan':
            result=scan(store,config['inbox'],dry_run=args.dry_run)
        elif args.command=='run-once':
            # Child inherits the exact configured numerical directory.
            os.environ['PDL_DATA_DIR']=str(config['data_dir'])
            result=run_once(config,notes_only=args.notes_only)
        elif args.command in ('pause','resume'):
            store.state('paused',args.command=='pause');result={'paused':store.state('paused')}
        elif args.command=='retry':
            with store.connect() as db:
                item=db.execute('SELECT path FROM items WHERE id=?',(args.item,)).fetchone()
                name=item[0] if item else args.item
                cursor=db.execute("UPDATE jobs SET status='queued',attempts=0,due=0,lease=0,error=NULL WHERE path=? AND status IN ('failed','needs_review','retry_wait')",(name,))
                result={'requeued':cursor.rowcount,'path':name}
        else:
            result={'items':store.items(),'health':store.health(),'last_run':store.state('last_run'),'paused':store.state('paused'),'fred':store.state('fred_due')}
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
