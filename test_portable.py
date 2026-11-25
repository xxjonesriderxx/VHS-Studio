"""Exercise the frozen EXE with no Python installation/environment on PATH.

All input is a two-second generated fixture. Never selects archive footage.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
exe=ROOT/'hybrid-dist/VHS Studio.exe'
manifest=json.loads((ROOT/'runtime-manifest.json').read_text('utf8'))
version=manifest['version']
stage=ROOT/'hybrid-stage'
shutil.copy2(exe,stage/'VHS Studio.exe')

def run(base,operation,env):
    file=base/f'{operation}.json'; events=base/f'{operation}.jsonl'
    output=base/'output'
    cfg=dict(source=str(base/'input'),output=str(output),deinterlace=True,method='QTGMC',
        replace=False,upscale=True,ocr=True,ocr_rate=2,recursive=True,limit=1,cpu_mode='gentle',archive=False,notifications=False)
    if operation=='scan':
        cfg['scan_only']=True
    else:
        prior=[json.loads(s) for s in (base/'scan.jsonl').read_text('utf8').splitlines()]
        cfg.update(scan_only=False,jobs=next(e['jobs'] for e in prior if e['event']=='plan'))
    file.write_text(json.dumps(cfg),encoding='utf8')
    proc=subprocess.run([str(stage/'VHS Studio.exe'),'--worker',str(file),str(events)],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd=base,timeout=240)
    data=[json.loads(s) for s in events.read_text('utf8').splitlines()]
    if proc.returncode or data[-1]['event'] not in ('plan','done') or data[-1].get('failed'):
        raise AssertionError(dict(code=proc.returncode,events=data[-5:],stderr=proc.stderr.decode(errors='replace')[-1000:]))
    print(operation,data[-1]['event'],flush=True)
    return data

with tempfile.TemporaryDirectory(prefix='VHS-portability-') as directory:
    base=Path(directory);(base/'input').mkdir()
    if '--standalone' in sys.argv:
        stage=base/'standalone';stage.mkdir()
        shutil.copy2(exe,stage/'VHS Studio.exe')
    shutil.copy2(ROOT/'test-source.mkv',base/'input/2001-01-01 - Original.mkv')
    env={k:v for k,v in os.environ.items() if k.upper() not in ('PYTHONPATH','PYTHONHOME')}
    env.update(LOCALAPPDATA=str(base/'local'),VHS_STUDIO_STATE_DIR=str(base/'state'),
               PYINSTALLER_RESET_ENVIRONMENT='1',PATH=os.environ.get('SystemRoot',r'C:\Windows')+r'\System32')
    described=subprocess.run([str(stage/'VHS Studio.exe'),'--describe'],capture_output=True,env=env,cwd=base,timeout=90)
    assert described.returncode==0,described.stderr
    options=json.loads(described.stdout)
    print('describe',options['version'],flush=True)
    run(base,'scan',env)
    run(base,'process',env)
    output=list((base/'output').glob('*.mp4'))
    assert len(output)==2,output
    assert (base/'output/_Administration/VHS-Studio/OCR-Fundstellen.json').exists()
    print('PASS: frozen QTGMC + OpenProteus + OCR without Python/PATH; '+('upstream auto-download' if '--standalone' in sys.argv else 'adjacent offline components'),flush=True)
