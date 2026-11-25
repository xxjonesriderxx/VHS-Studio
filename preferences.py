"""Per-user preferences and opt-in login startup. Never requires elevation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def state_dir():
    return Path(os.environ.get('VHS_STUDIO_STATE_DIR') or Path(os.environ.get('LOCALAPPDATA', Path.home()))/'VHS Studio')

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text('utf8'))
    except (OSError, ValueError):
        return {} if default is None else default

def write_json(path, value):
    import uuid
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

def load():
    return read_json(state_dir()/'settings.json')

def save(settings):
    write_json(state_dir()/'settings.json', settings)

def startup_link():
    import win32com.client
    shell=win32com.client.Dispatch('WScript.Shell')
    return Path(shell.SpecialFolders('Startup'))/'VHS Studio - Background.lnk'

def startup_active():
    return bool(read_json(state_dir()/'autostart.json').get('enabled')) and startup_link().exists()

def configure_startup(config=None, enabled=True, link_path=None):
    profile=state_dir()/'autostart.json'
    link=Path(link_path) if link_path is not None else startup_link()
    if not enabled:
        write_json(profile, dict(enabled=False))
        link.unlink(missing_ok=True)
        return
    if not config:
        raise ValueError('No restoration configuration')
    config={k:v for k,v in config.items() if k not in ('jobs','scan_only')}
    write_json(profile, dict(enabled=True, config=config))
    import win32com.client
    shell=win32com.client.Dispatch('WScript.Shell')
    shortcut=shell.CreateShortcut(str(link))
    args=[]
    if os.environ.get('VHS_STUDIO_BOOTSTRAP')=='1':
        shortcut.TargetPath=os.environ['VHS_STUDIO_EXE']
    elif not getattr(sys,'frozen',False):
        shortcut.TargetPath=str(Path(sys.executable).with_name('pythonw.exe'))
        args.append(str(Path(__file__).with_name('app.py')))
    else:
        shortcut.TargetPath=sys.executable
    shortcut.Arguments=subprocess.list2cmdline(args+['--autostart'])
    shortcut.WorkingDirectory=str(Path(sys.executable).parent)
    shortcut.WindowStyle=7
    shortcut.Description='VHS Studio: saved restoration profile, after user sign-in'
    shortcut.Save()

def file_identity(path):
    p=Path(path)
    stat=p.stat()
    return [str(p.resolve()), stat.st_size, stat.st_mtime_ns]

def job_key(cfg, job):
    return hashlib.sha256(json.dumps([cfg, file_identity(job['input']), file_identity(job['path'])],sort_keys=True).encode()).hexdigest()

def run_startup():
    """One batch per login. Completion ledger prevents repeats in export mode."""
    import msvcrt
    from mcp_server import serve
    root=state_dir(); root.mkdir(parents=True, exist_ok=True)
    def call(tool, **arguments):
        return serve(request=dict(tool=tool,arguments=arguments))
    def wait(job):
        while True:
            status=call('get_job_status',job_id=job['id'])
            if not status['running']:
                return status
            time.sleep(.5)
    def log(**fields):
        write_json(root/'autostart-status.json', dict(updated=time.strftime('%Y-%m-%d %H:%M:%S'), **fields))
        if fields.get('state') in ('nothing_pending','error') and cfg.get('notifications',True):
            from notifications import send
            de=cfg.get('language','en')=='de'
            if fields['state']=='nothing_pending':
                send('VHS Studio · Autostart abgeschlossen' if de else 'VHS Studio · Auto-start complete',
                     'Keine ausstehenden Dateien für diesen Lauf.' if de else 'No pending recordings for this batch.')
            else:
                send('VHS Studio · Autostart fehlgeschlagen' if de else 'VHS Studio · Auto-start failed',fields.get('error',''))
    cfg={}
    with (root/'autostart.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            return
        try:
            profile=read_json(root/'autostart.json')
            if not profile.get('enabled'):
                return
            cfg=profile['config']
            options={k:v for k,v in cfg.items() if k not in ('source','output','gentle')}
            limit=options.get('limit',2)
            options['limit']=0
            log(state='scanning')
            scan=call('scan_folder',source=cfg['source'],output=cfg['output'],options=options)
            status=wait(scan)
            plan=status.get('completion') or {}
            if plan.get('event')!='plan':
                raise RuntimeError(str(plan))
            ledger=read_json(root/'autostart-completed.json')
            pending=[]
            keys=[]
            for job in plan['jobs']:
                key=job_key(cfg,job)
                old=ledger.get(key)
                try:
                    complete=bool(old) and all(file_identity(p[0])==p for p in old['outputs'])
                except OSError:
                    complete=False
                if not complete:
                    pending.append(job); keys.append(key)
                    if limit and len(pending)>=limit:
                        break
            if not pending:
                log(state='nothing_pending',scan_id=scan['id'],errors=plan.get('errors',[]))
                return
            # Save the filtered plan in the scan's private job file. Existing
            # start_processing uses that plan; the engine still takes its lock.
            from mcp_server import JOBS
            with (JOBS/scan['id']/'events.jsonl').open('a',encoding='utf8') as stream:
                stream.write(json.dumps(dict(event='plan',jobs=pending,errors=plan.get('errors',[])))+'\n')
            job=call('start_processing',scan_id=scan['id'],origin='autostart')
            log(state='processing',job_id=job['id'],count=len(pending))
            status=wait(job)
            # Keep each successful file even if another file failed.
            import sqlite3
            from archive_layout import data_folder
            database=data_folder(cfg['output'])/'VHS-Studio.sqlite3'
            for result in status['results']:
                if result['status']!='Fertig':
                    continue
                outputs=[result['detail']]
                if database.exists():
                    with sqlite3.connect(database) as db:
                        row=db.execute('SELECT details FROM runs WHERE input=? ORDER BY rowid DESC LIMIT 1', (pending[result['index']]['path'],)).fetchone()
                        if row:
                            outputs += [f['path'] for f in json.loads(row[0])['files']]
                ledger[keys[result['index']]]=dict(outputs=[file_identity(p) for p in sorted(set(outputs))])
                write_json(root/'autostart-completed.json', ledger)
            log(state='finished',job_id=job['id'],completion=status.get('completion'),results=status['results'])
        except Exception as error:
            log(state='error',error=str(error))
