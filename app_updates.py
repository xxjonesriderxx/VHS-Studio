"""Stable GitHub release updates, staged and verified before user-local replacement."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPSHandler
import ssl
from app_version import VERSION,REPOSITORY
from runtime_components import CheckedRedirect,allowed_url,digest

HOSTS={'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}


def running_executable():
    if os.environ.get('VHS_STUDIO_BOOTSTRAP')=='1':
        value=os.environ.get('VHS_STUDIO_EXE')
        if not value or Path(value).suffix.lower()!='.exe' or Path(value).name.lower() in ('python.exe','pythonw.exe'):
            raise ValueError('Missing bootstrap application executable; refusing to update Python.')
        return Path(value).resolve()
    return Path(sys.executable).resolve()

def version_key(value):
    import re
    from datetime import date
    match=re.fullmatch(r'(\d{4}-\d{2}-\d{2})(?:-(\d+))?',value)
    if not match:
        raise ValueError('Release version must be YYYY-MM-DD with an optional numeric build suffix')
    day=date.fromisoformat(match[1])
    return (day.year,day.month,day.day,int(match[2] or 0))

def opener():
    return build_opener(HTTPSHandler(context=ssl.create_default_context()),CheckedRedirect(HOSTS))

def latest():
    url=f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
    try:
        with opener().open(Request(url,headers={'User-Agent':'VHS-Studio','Accept':'application/vnd.github+json'}),timeout=10) as response:
            data=json.load(response)
    except HTTPError as error:
        if error.code==404:
            return None
        raise
    if data.get('draft') or data.get('prerelease') or version_key(data['tag_name'])<=version_key(VERSION):
        return None
    number=data['tag_name']
    asset=next((a for a in data['assets'] if a['name']==f'VHS-Studio-{number}.exe'),None)
    if not asset or not str(asset.get('digest','')).startswith('sha256:'):
        raise ValueError('Release has no verifiable standalone EXE; update was not installed')
    checksum=asset['digest'].split(':',1)[1]
    if len(checksum)!=64 or any(c not in '0123456789abcdef' for c in checksum):
        raise ValueError('Invalid release asset checksum')
    allowed_url(asset['browser_download_url'],HOSTS)
    return dict(version=number,url=asset['browser_download_url'],sha256=checksum,size=asset['size'])

def stage(info, progress=None):
    root=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'VHS Studio'/'updates'/info['version']
    root.mkdir(parents=True,exist_ok=True)
    target=root/f"VHS-Studio-{info['version']}.exe"
    if target.exists() and digest(target)==info['sha256']:
        return target
    if not 0<info['size']<1024*1024*1024:
        raise ValueError('Invalid update size')
    import shutil,uuid
    if shutil.disk_usage(root).free<info['size']*2+32*1024*1024:
        raise RuntimeError('Not enough free disk space for application update')
    tmp=root/(uuid.uuid4().hex+'.part')
    try:
        with opener().open(Request(info['url'],headers={'User-Agent':'VHS-Studio'}),timeout=45) as source,tmp.open('wb') as sink:
            count=0
            for block in iter(lambda:source.read(1024*1024),b''):
                count+=len(block)
                if count>info['size']:
                    raise ValueError('Update exceeds declared size')
                sink.write(block)
                if progress:
                    progress(count,info['size'])
        if count!=info['size'] or digest(tmp)!=info['sha256']:
            raise ValueError('Update integrity check failed')
        target_tmp=tmp
        target_tmp.replace(target)
        return target
    finally:
        tmp.unlink(missing_ok=True)

def launch_helper(staged,info,restart_args=None):
    target=running_executable()
    import tempfile
    with tempfile.TemporaryFile(dir=target.parent):
        pass
    request=staged.parent/('apply-'+str(os.getpid())+'.json')
    request.write_text(json.dumps(dict(target=str(target),old_sha256=digest(target),new_sha256=info['sha256'],
        restart_args=restart_args or [])),encoding='utf8')
    subprocess.Popen([str(staged),'--apply-update',str(request)],creationflags=subprocess.CREATE_NO_WINDOW,
        env=dict(os.environ,PYINSTALLER_RESET_ENVIRONMENT='1'))

def apply(request_path):
    """Runs in the downloaded EXE while the old app exits. Never terminates jobs."""
    request=Path(request_path).resolve()
    data=json.loads(request.read_text('utf8'))
    source=running_executable();target=Path(data['target']).resolve()
    if target.name.lower() in ('python.exe','pythonw.exe'):
        raise ValueError('Refusing to replace a Python interpreter as an application update.')
    if target.suffix.lower()!='.exe' or source==target or digest(source)!=data['new_sha256']:
        raise ValueError('Invalid application update request')
    if not target.exists() or digest(target)!=data['old_sha256']:
        raise ValueError('Application changed while update was being staged')
    backup=target.with_name(target.name+'.previous')
    log=request.parent/'update-result.json'
    # Wait for the old application and its one-file bootloader to release it.
    for attempt in range(120):
        try:
            if digest(target)!=data['old_sha256']:
                raise RuntimeError('Application changed before update installation')
            if backup.exists():
                backup.unlink()
            target.rename(backup)
            break
        except PermissionError:
            time.sleep(1)
    else:
        log.write_text(json.dumps(dict(ok=False,error='Application is still in use or its folder is read-only; existing app was retained.')))
        return
    try:
        import shutil,uuid
        tmp=target.with_name(target.name+'.'+uuid.uuid4().hex+'.update')
        shutil.copyfile(source,tmp)
        if digest(tmp)!=data['new_sha256']:
            raise ValueError('Replacement integrity check failed')
        tmp.replace(target)
        subprocess.Popen([str(target),*data.get('restart_args',[])],creationflags=subprocess.CREATE_NO_WINDOW,
            env=dict(os.environ,PYINSTALLER_RESET_ENVIRONMENT='1'))
        log.write_text(json.dumps(dict(ok=True,version=VERSION)))
    except BaseException:
        if target.exists():
            target.unlink()
        backup.rename(target)
        raise

def other_instances():
    import psutil
    own={os.getpid(),os.getppid()}
    target=running_executable()
    for proc in psutil.process_iter(['pid','exe']):
        try:
            if proc.info['pid'] not in own and proc.info['exe'] and Path(proc.info['exe']).resolve()==target:
                return True
        except (psutil.Error,OSError):
            pass
    return False
