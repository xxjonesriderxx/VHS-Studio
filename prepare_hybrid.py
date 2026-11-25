"""Build offline component folders from pinned ORIGINAL upstream archives.

Only our manifest and code belong in Git; staging/downloads are release assets.
"""
import hashlib
import json
from pathlib import Path
import shutil
from urllib.request import urlopen
from urllib.error import HTTPError
import zipfile

HERE=Path(__file__).resolve().parent
VERSION='0.3.0'
STAGE=HERE/'hybrid-stage'
DOWNLOADS=HERE/'upstream-cache'
PACKAGES=[('VapourSynth','82'),('vapoursynth-bestsource','23'),('vapoursynth-fmtconv','31.1'),
    ('vapoursynth-znedi3','3.3'),('vapoursynth-dfttest2-cpu','11.1.0'),('vapoursynth-awarp','3.1'),
    ('vapoursynth-deblock','9.0'),('vapoursynth-resize2','0.5.1'),('vapoursynth-akarin','1.5.0'),
    ('vapoursynth-mvutensils','9'),('vapoursynth-zsmooth','0.20.0'),('vapoursynth-hysteresis','1.4.0'),
    ('vapoursynth-vszip','24.0.0')]

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def download(url, checksum=None):
    DOWNLOADS.mkdir(exist_ok=True)
    path=DOWNLOADS/url.rsplit('/',1)[-1]
    if not path.exists() or checksum and sha(path)!=checksum:
        print('Download',url,flush=True)
        tmp=path.with_suffix(path.suffix+'.part')
        with urlopen(url,timeout=60) as source,tmp.open('wb') as target:
            shutil.copyfileobj(source,target,1024*1024)
        if checksum and sha(tmp)!=checksum:
            raise ValueError('Upstream checksum mismatch: '+url)
        tmp.replace(path)
    return path

def archive(url, path, mapping, origin):
    files={}
    with zipfile.ZipFile(path) as z:
        for source,dest in mapping.items():
            blob=z.read(source)
            files[dest]=dict(size=len(blob),sha256=hashlib.sha256(blob).hexdigest())
    return dict(url=url,size=path.stat().st_size,sha256=sha(path),members=mapping,files=files,origin=origin)

def install_stage(name, item):
    root=STAGE/'components'/VERSION/name
    root.mkdir(parents=True,exist_ok=True)
    path=DOWNLOADS/item['url'].rsplit('/',1)[-1]
    with zipfile.ZipFile(path) as z:
        for member,dest in item['members'].items():
            out=root/dest;out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(z.read(member))

def main():
    packs={}
    # Versioned Gyan release builds (linked by ffmpeg.org), never git snapshots.
    version=urlopen('https://www.gyan.dev/ffmpeg/builds/release-version',timeout=30).read().decode().strip()
    import re
    if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?',version):
        raise ValueError('Unexpected FFmpeg release version: '+version)
    url=f'https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-{version}-essentials_build.zip'
    checksum=urlopen(url+'.sha256',timeout=30).read().decode().split()[0]
    # The versioned GitHub mirror is published by the same Gyan maintainer.
    url=f'https://github.com/GyanD/codexffmpeg/releases/download/{version}/ffmpeg-{version}-essentials_build.zip'
    path=download(url,checksum)
    with zipfile.ZipFile(path) as z:
        mapping={}
        for name in z.namelist():
            if name.endswith(('/bin/ffmpeg.exe','/bin/ffprobe.exe')):
                mapping[name]='bin/'+name.rsplit('/',1)[-1]
            elif name.lower().endswith(('/license','/license.txt','/readme.txt')):
                mapping[name]='licenses/ffmpeg/'+name.rsplit('/',1)[-1]
    if not {'bin/ffmpeg.exe','bin/ffprobe.exe'}.issubset(mapping.values()):
        raise ValueError('FFmpeg release archive is missing required tools')
    packs['media']=[archive(url,path,mapping,'https://ffmpeg.org/download.html')]
    packs['qtgmc']=[]
    for package,version in PACKAGES:
        try:
            metadata=json.load(urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=30))
        except HTTPError as error:
            if error.code!=404:
                raise
            project=json.load(urlopen(f'https://pypi.org/pypi/{package}/json',timeout=30))
            stable=[v for v in project['releases'] if re.fullmatch(r'\d+(?:\.\d+)*',v)]
            version=max(stable,key=lambda v:tuple(map(int,v.split('.'))))
            print('Public stable version',package,version,flush=True)
            metadata=json.load(urlopen(f'https://pypi.org/pypi/{package}/{version}/json',timeout=30))
        candidates=[x for x in metadata['urls'] if x['filename'].endswith('win_amd64.whl')
                    and ('cp312' in x['filename'] or '-py3-' in x['filename'])]
        if len(candidates)!=1:
            raise ValueError(f'Expected one compatible wheel for {package}: {[x["filename"] for x in candidates]}')
        entry=candidates[0];path=download(entry['url'],entry['digests']['sha256'])
        mapping={}
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                low=name.lower()
                if name.endswith('/') or low.endswith(('.pdb','.pyi')):
                    continue
                if '.avx2.dll' in low or '_avx2.dll' in low or '.zn4.dll' in low or '_zn4.dll' in low:
                    continue
                if name.startswith('vapoursynth/') and low.endswith(('.dll','.pyd','.py','.bin')):
                    mapping[name]=name
                elif '.dist-info/' in name and any(word in low for word in ('license','copying','notice','metadata')):
                    mapping[name]='licenses/'+name
        packs['qtgmc'].append(archive(entry['url'],path,mapping,f'https://pypi.org/project/{package}/{version}/'))
    result=dict(version=VERSION,allowed_hosts=['www.gyan.dev','gyan.dev','github.com',
        'release-assets.githubusercontent.com','objects.githubusercontent.com','files.pythonhosted.org'],packs={})
    for name,archives in packs.items():
        files={}
        for item in archives:
            overlap=set(files)&set(item['files'])
            if overlap:
                raise ValueError('Conflicting runtime files: '+str(overlap))
            files.update(item['files'])
            install_stage(name,item)
        pack_hash=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
        result['packs'][name]=dict(files=files,archives=archives,size=sum(a['size'] for a in archives),sha256=pack_hash)
    # Compact OpenProteus remains inside the base EXE (only 1.2 MB).
    (HERE/'runtime-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps({k:dict(download_MB=v['size']/1e6,installed_MB=sum(f['size'] for f in v['files'].values())/1e6) for k,v in result['packs'].items()},indent=2),flush=True)

if __name__=='__main__':
    main()
