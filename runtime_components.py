"""Pinned, app-local runtime packs. No installers, elevation or system PATH edits."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import ssl
import sys
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
import zipfile
import uuid

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
EXE_DIR=Path(sys.executable).parent if getattr(sys,'frozen',False) else ROOT
_ready={}
_dll_handles=[]

def manifest():
    if not getattr(sys,'frozen',False):
        return None
    path=ROOT/'runtime-manifest.json'
    return json.loads(path.read_text('utf8')) if path.exists() else None

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def safe_relative(value):
    p=PurePosixPath(value)
    if not p.parts or p.is_absolute() or any(x in ('..','.') or ':' in x or '\\' in x for x in p.parts):
        raise ValueError('Unsafe component path')
    return Path(*p.parts)

def cache_root():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()))/'VHS Studio'/'components'

def candidates(name, data):
    pack=data['packs'][name]
    return [EXE_DIR/'components'/data['version']/name,
            cache_root()/data['version']/(name+'-'+pack['sha256'][:16])]

def valid(folder, pack, full=True):
    for name, spec in pack['files'].items():
        path=Path(folder)/safe_relative(name)
        if not path.is_file() or path.stat().st_size!=spec['size']:
            return False
        if full and digest(path)!=spec['sha256']:
            return False
    return True

def component_root(name):
    data=manifest()
    if not data:
        return ROOT
    if name in _ready:
        return _ready[name]
    for folder in candidates(name,data):
        if valid(folder,data['packs'][name],full=False):
            return folder
    return candidates(name,data)[-1]

def asset(name, relative):
    return component_root(name)/relative

def allowed_url(url, hosts):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError('Download URL is not on the pinned HTTPS allowlist')

class CheckedRedirect(HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts=hosts
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_url(newurl,self.hosts)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def unpack_verified(archive, target, pack):
    """Extract only declared files, with bounded sizes and no path traversal."""
    if digest(archive)!=pack['sha256']:
        raise ValueError('Component archive checksum mismatch')
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        names=[i.filename for i in entries]
        members=pack.get('members',{key:key for key in pack['files']})
        if len(names)!=len(set(names)) or not set(members).issubset(names):
            raise ValueError('Missing or duplicate component archive entries')
        for member,destination in members.items():
            item=z.getinfo(member)
            spec=pack['files'][destination]
            rel=safe_relative(destination)
            if item.file_size!=spec['size'] or item.is_dir() or (item.external_attr>>16)&0o170000==0o120000:
                raise ValueError('Invalid component archive entry')
            dest=Path(target)/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as source,dest.open('xb') as sink:
                shutil.copyfileobj(source,sink,1024*1024)
            if digest(dest)!=spec['sha256']:
                raise ValueError('Extracted component checksum mismatch')

def ensure(name, progress=None):
    data=manifest()
    if not data:
        return ROOT  # development tree; release always embeds a manifest
    if name=='openproteus' and name not in data['packs']:
        if not (ROOT/'model/2x_OpenProteus_Compact_i2_70K.bin').is_file():
            raise RuntimeError('Embedded OpenProteus model is damaged. Download the application again.')
        return ROOT
    if name in _ready:
        return _ready[name]
    pack=data['packs'][name]
    for folder in candidates(name,data):
        if valid(folder,pack):
            _ready[name]=folder
            return folder
    target=candidates(name,data)[-1]
    target.parent.mkdir(parents=True,exist_ok=True)
    import msvcrt
    with target.with_suffix('.lock').open('a+b') as lock:
        lock.seek(0)
        if not lock.read(1):
            lock.write(b'0');lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            raise RuntimeError('Another VHS Studio process is preparing this component. Try again after it finishes.')
        if valid(target,pack):
            _ready[name]=target
            return target
        archives=pack.get('archives',[pack])
        if not archives or any(not item.get('url') for item in archives):
            raise RuntimeError(f"Missing component: {name}. Restore the components folder from the full offline ZIP; no upstream source configured.")
        hosts=set(data['allowed_hosts'])
        for item in archives:
            allowed_url(item['url'],hosts)
        free=shutil.disk_usage(target.parent).free
        needed=pack['size']+sum(x['size'] for x in pack['files'].values())+32*1024*1024
        if free<needed:
            raise RuntimeError(f'Not enough free disk space for {name}: {needed} bytes required')
        if progress:
            progress(name,0,pack['size'])
        with tempfile.TemporaryDirectory(prefix='.download-',dir=target.parent) as directory:
            tmp=Path(directory);stage=tmp/'unpacked';stage.mkdir()
            opener=build_opener(HTTPSHandler(context=ssl.create_default_context()),CheckedRedirect(hosts))
            completed=0
            for index,item in enumerate(archives):
                archive=tmp/f'{index}.zip'
                with opener.open(Request(item['url'],headers={'User-Agent':'VHS-Studio'}),timeout=45) as source,archive.open('wb') as sink:
                    count=0;reported=0
                    for block in iter(lambda:source.read(256*1024),b''):
                        count+=len(block)
                        if count>item['size']:
                            raise ValueError('Download exceeds declared size')
                        sink.write(block)
                        if progress and (count-reported>=1024*1024 or count==item['size']):
                            progress(name,completed+count,pack['size']);reported=count
                    if count!=item['size']:
                        raise ValueError('Incomplete component download')
                unpack_verified(archive,stage,item)
                completed+=count
            if not valid(stage,pack):
                raise ValueError('Incomplete component installation')
            # Never overwrite tools loaded by another process. A damaged cache
            # can only be replaced after verifying the complete new pack.
            if target.exists():
                backup=target.with_name(target.name+'.damaged-'+uuid.uuid4().hex)
                target.rename(backup)
                try:
                    stage.rename(target)
                except BaseException:
                    backup.rename(target)
                    raise
                if backup.resolve().parent!=target.resolve().parent or not backup.name.startswith(target.name+'.damaged-'):
                    raise RuntimeError('Unsafe cache cleanup path')
                shutil.rmtree(backup)
            else:
                stage.rename(target)
        _ready[name]=target
        return target

def activate_qtgmc():
    folder=ensure('qtgmc')
    if manifest():
        if str(folder) not in sys.path:
            sys.path.insert(0,str(folder))
        for p in (folder,folder/'vapoursynth'):
            if p.is_dir():
                _dll_handles.append(os.add_dll_directory(str(p)))
        os.environ['PATH']=str(folder/'vapoursynth')+os.pathsep+os.environ.get('PATH','')
    return folder

def prepare(config, progress=None):
    ensure('media',progress)
    if config.get('scan_only'):
        return
    if config.get('replace') or config.get('deinterlace') and config.get('method')=='QTGMC':
        ensure('qtgmc',progress)
        activate_qtgmc()
    if config.get('upscale'):
        ensure('openproteus',progress)

def status():
    data=manifest()
    if not data:
        return dict(mode='development',packs=[])
    return dict(mode='hybrid',version=data['version'],packs=[dict(name=name,
        present=any(valid(p,pack,full=False) for p in candidates(name,data)),
        download_bytes=pack['size'],download_configured=all(bool(x.get('url')) for x in pack.get('archives',[pack])))
        for name,pack in data['packs'].items()])
