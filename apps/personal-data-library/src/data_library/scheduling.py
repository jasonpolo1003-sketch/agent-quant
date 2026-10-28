"""Owned fixed-command Windows task. Registration is never a startup action."""
import getpass
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

PROJECT=Path(__file__).resolve().parents[2]
TASK='\\PersonalDataLibrary\\intake'
NS={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}


def task_xml(root=PROJECT, user=None):
    root=Path(root)
    user=escape(user or getpass.getuser())
    python=escape(str(root/'.venv/Scripts/python.exe'))
    script=escape('"'+str(root/'scripts/run_intake_once.py')+'"')
    return f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="{NS['t']}">
<RegistrationInfo><Description>Personal Data Library bounded intake only. No Quant execution.</Description><URI>{TASK}</URI></RegistrationInfo>
<Triggers><TimeTrigger><Repetition><Interval>PT2M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>2026-10-28T00:00:00</StartBoundary><Enabled>true</Enabled></TimeTrigger><LogonTrigger><Enabled>true</Enabled><UserId>{user}</UserId></LogonTrigger></Triggers>
<Principals><Principal id="Author"><UserId>{user}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><Enabled>true</Enabled><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT90S</ExecutionTimeLimit></Settings>
<Actions Context="Author"><Exec><Command>{python}</Command><Arguments>{script}</Arguments><WorkingDirectory>{escape(str(root))}</WorkingDirectory></Exec></Actions></Task>'''


def invoke(args,runner):
    return runner(['schtasks.exe',*args],capture_output=True,text=True,timeout=15)


def status(runner=subprocess.run):
    try:
        proc=invoke(['/Query','/TN',TASK,'/XML'],runner)
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'task':TASK,'enabled':None,'registered':None,'drift':None,'error':str(exc)}
    if proc.returncode:
        error=(proc.stderr or proc.stdout).strip()
        absent='cannot find' in error.lower() or 'does not exist' in error.lower()
        return {'task':TASK,'registered':False if absent else None,'enabled':False if absent else None,'drift':False if absent else None,'error':error}
    try:
        tree=ET.fromstring(proc.stdout)
        fields={name:tree.findtext(path,namespaces=NS) for name,path in {
            'command':'.//t:Exec/t:Command','arguments':'.//t:Exec/t:Arguments','working_directory':'.//t:Exec/t:WorkingDirectory',
            'non_overlap':'.//t:MultipleInstancesPolicy','catch_up':'.//t:StartWhenAvailable','execution_limit':'.//t:ExecutionTimeLimit',
            'interval':'.//t:TimeTrigger/t:Repetition/t:Interval','logon_type':'.//t:Principal/t:LogonType'}.items()}
        expected={'command':str(PROJECT/'.venv/Scripts/python.exe'),'arguments':'"'+str(PROJECT/'scripts/run_intake_once.py')+'"','working_directory':str(PROJECT),'non_overlap':'IgnoreNew','catch_up':'true','execution_limit':'PT90S','interval':'PT2M','logon_type':'InteractiveToken'}
        def normalized(v): return (v or '').replace('\\','/').casefold()
        drift=any(normalized(fields[k])!=normalized(v) for k,v in expected.items()) or len(tree.findall('t:Actions/*',NS))!=1
        return {'task':TASK,'registered':True,'enabled':tree.findtext('t:Settings/t:Enabled',namespaces=NS)=='true','drift':drift,**fields}
    except ET.ParseError as exc:
        return {'task':TASK,'registered':True,'enabled':None,'drift':True,'error':str(exc)}


def enable(confirmed=False,runner=subprocess.run):
    if not confirmed:
        raise PermissionError('Separate user activation confirmation required. No task registered.')
    current=status(runner)
    if current['registered'] is None or current.get('drift'):
        raise ValueError('Cannot safely register: unknown or drifted task; inspect first')
    if current['registered']:
        raise ValueError('Task already exists. Inspect it instead of overwriting.')
    scratch=PROJECT/'data/locks'
    scratch.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=scratch,suffix='.xml',delete=False) as f:
        path=Path(f.name)
        f.write(task_xml().encode('utf-16'))
    try:
        proc=invoke(['/Create','/TN',TASK,'/XML',str(path)],runner)
        if proc.returncode: raise RuntimeError(proc.stderr or proc.stdout)
    finally:
        path.unlink(missing_ok=True)
    readback=status(runner)
    if readback.get('enabled') is not True or readback.get('drift'):
        raise RuntimeError(f'Task readback failed: {readback}')
    return readback


def disable(runner=subprocess.run):
    current=status(runner)
    if current['registered'] is False: return current
    if current['registered'] is None or current.get('drift'):
        raise ValueError('Unknown/drifted task; refusing to modify it')
    proc=invoke(['/Change','/TN',TASK,'/Disable'],runner)
    if proc.returncode: raise RuntimeError(proc.stderr or proc.stdout)
    readback=status(runner)
    if readback.get('enabled') is not False: raise RuntimeError('Disable readback failed')
    return readback
