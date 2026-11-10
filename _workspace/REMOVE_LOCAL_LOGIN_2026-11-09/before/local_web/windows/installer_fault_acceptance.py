"""Actual installer interruption/read-only recovery on a new fixture directory."""
import argparse
import json
from pathlib import Path
import stat
import subprocess
import time

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--installer',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    target=out/'Программа';installer=args.installer.resolve()
    rows=[]
    def command(name):return [str(installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
        '/DIR='+str(target),'/LOG='+str(out/(name+'.log'))]
    process=subprocess.Popen(command('interrupted'))
    killed=False
    # Payload extraction/integrity checking can exceed 12 seconds on a cold
    # Windows host. Bound the observation by wall clock, keeping the required
    # real-copy checkpoint (and refusal to claim PASS if it is not observed).
    deadline=time.monotonic()+120
    while time.monotonic()<deadline:
        if process.poll() is not None:break
        stages=list(target.glob('staging-*')) if target.exists() else []
        if stages and any(stages[0].iterdir()):
            # Only this known test process and its installation helper tree.
            stop=subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=15)
            process.wait(timeout=20);killed=stop.returncode==0;break
        time.sleep(.01)
    if not killed:raise AssertionError('Did not observe and interrupt real installer copy; not a PASS')
    if (target/'current.json').exists():raise AssertionError('Unexpected commit before interruption checkpoint')
    rows.append({'scenario':'actual_setup_process_tree_interruption_during_copy','status':'PASS','pid':process.pid,'exit':process.returncode})
    result=subprocess.run(command('recovery'),timeout=180)
    if result.returncode:raise AssertionError('Interrupted setup recovery failed: '+str(result.returncode))
    pointer=target/'current.json';before=pointer.read_bytes()
    rows.append({'scenario':'actual_setup_recovery','status':'PASS','exit':result.returncode})
    pointer.chmod(stat.S_IREAD)
    try:
        result=subprocess.run(command('readonly'),timeout=180)
        if result.returncode==0 or pointer.read_bytes()!=before:raise AssertionError('Read-only install not fail-closed')
        rows.append({'scenario':'actual_readonly_pointer','status':'PASS','exit':result.returncode})
    finally:pointer.chmod(stat.S_IREAD|stat.S_IWRITE)
    result=subprocess.run(command('readonly-retry'),timeout=180)
    if result.returncode or pointer.read_bytes()!=before:raise AssertionError('Read-only retry failed')
    rows.append({'scenario':'actual_readonly_retry','status':'PASS','exit':result.returncode})
    uninstall=next((target/'uninstall').glob('unins*.exe'))
    result=subprocess.run([str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',
        '/LOG='+str(out/'uninstall.log')],timeout=120)
    if result.returncode:raise AssertionError('Fixture uninstall failed')
    (out/'RESULT.json').write_text(json.dumps({'status':'PASS','scenarios':rows,
        'physical_power_loss':'NOT RUN','real_disk_full':'NOT RUN; separate injection does not substitute'},indent=2)+'\n','utf-8')
    print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
