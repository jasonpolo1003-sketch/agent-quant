"""Verify local intake, optionally create an isolated paired-catalog backup."""
import argparse
import json
from pathlib import Path
from data_library.worker import load_config
from data_library.intake_verify import verify,backup
from data_library.scheduling import status

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data-dir',type=Path)
parser.add_argument('--backup-to',type=Path)
args=parser.parse_args()
config=load_config()
root=args.data_dir or Path(config['data_dir'])
report=verify(root,None if args.data_dir else config['inbox'])
report['scheduler']=status()
if args.backup_to:
    report['backup_restore']=backup(root,args.backup_to)
    report['ok']=report['ok'] and report['backup_restore']['ok']
output=Path(__file__).resolve().parents[1]/'reports/intake-acceptance.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(report,indent=2,ensure_ascii=False))
raise SystemExit(0 if report['ok'] else 1)
