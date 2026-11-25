"""Collect reproducible verification evidence without claiming production release."""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from appforge.state import atomic, now
from appforge.planning import source_hash


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Include independent schemas, every blueprint, and real Chromium checks')
    args = parser.parse_args()
    commands = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                [sys.executable, 'scripts/check_repository.py']]
    if args.full:
        commands.extend([[sys.executable, 'scripts/check_repository.py', '--jsonschema'],
                         [sys.executable, 'scripts/test_blueprints.py'],
                         [sys.executable, 'scripts/browser_smoke.py']])
    report = {'at':now(),'sourceHash':source_hash(),'environment':{'python':platform.python_version(),'os':platform.platform()},'commands':[],'passed':True,'productionReady':False}
    for command in commands:
        print('Running: '+' '.join(command),flush=True)
        started=time.monotonic()
        result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=180)
        record={'command':command,'exitCode':result.returncode,'seconds':round(time.monotonic()-started,3),'passed':result.returncode==0,'output':result.stdout+result.stderr}
        report['commands'].append(record);report['passed'] &= record['passed']
        print(('PASS' if record['passed'] else 'FAIL')+f" ({record['seconds']}s)",flush=True)
        if not record['passed']: print(record['output'],flush=True)
    path=ROOT/'artifacts'/'verification-report.json';atomic(path,report)
    print(json.dumps({'passed':report['passed'],'report':str(path)},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
