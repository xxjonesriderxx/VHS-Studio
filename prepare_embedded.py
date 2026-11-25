"""Fetch small bundled assets from their upstream sources, never from a local app."""
import hashlib
import json
from pathlib import Path
import tarfile
from urllib.request import urlopen
import zipfile
from prepare_hybrid import download, HERE

def main():
    manifest=HERE/'embedded-manifest.json'
    if manifest.exists():
        data=json.loads(manifest.read_text('utf8'))
    else:
        meta=json.load(urlopen('https://pypi.org/pypi/upscale-ncnn-py/1.2.0/json',timeout=30))
        entry=next(x for x in meta['urls'] if x['filename'].endswith('cp312-none-win_amd64.whl'))
        model_url='https://github.com/TNTwise/real-video-enhancer-models/releases/download/models/2x_OpenProteus_Compact_i2_70K.tar.gz'
        model=download(model_url)
        data=dict(inference=dict(url=entry['url'],sha256=entry['digests']['sha256']),
            model=dict(url=model_url,sha256=hashlib.sha256(model.read_bytes()).hexdigest()),
            license=dict(url='https://raw.githubusercontent.com/Sirosky/Upscale-Hub/main/LICENSE.md'))
        license_data=urlopen(data['license']['url'],timeout=30).read()
        data['license']['sha256']=hashlib.sha256(license_data).hexdigest()
        manifest.write_text(json.dumps(data,indent=2),encoding='utf8')
    wheel=download(data['inference']['url'],data['inference']['sha256'])
    vendor=HERE/'vendor/upscale_ncnn_py';vendor.mkdir(parents=True,exist_ok=True)
    licenses=HERE/'assets/licenses';licenses.mkdir(parents=True,exist_ok=True)
    # Preserve notices from bundled Python dependencies, including build tools'
    # runtime exceptions. No local install metadata or direct_url files are copied.
    import sys
    for entry in dict.fromkeys(sys.path):
        parent=Path(entry)
        if not parent.is_dir():
            continue
        for metadata in parent.glob('*.dist-info'):
            for notice in metadata.rglob('*'):
                if notice.is_file() and any(word in notice.name.lower() for word in ('license','copying','notice')):
                    dest=licenses/metadata.name/notice.relative_to(metadata)
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(notice.read_bytes())
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():
        (licenses/'Python-LICENSE.txt').write_bytes(python_license.read_bytes())
    if (HERE/'LICENSE').exists():
        (licenses/'VHS-Studio-MIT.txt').write_bytes((HERE/'LICENSE').read_bytes())
    import importlib.util
    winrt=importlib.util.find_spec('winrt')
    if winrt and winrt.submodule_search_locations:
        import shutil
        original=Path(next(iter(winrt.submodule_search_locations)))
        dest=HERE/'vendor/winrt'
        if original.resolve()!=dest.resolve():
            shutil.copytree(original,dest,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    if not (HERE/'vendor/winrt').exists():
        raise ValueError('Windows OCR projection packages are missing; install requirements-build.txt')
    with zipfile.ZipFile(wheel) as z:
        for name in z.namelist():
            if name.startswith('upscale_ncnn_py/') and name.endswith(('.pyd','.dll')):
                (vendor/Path(name).name).write_bytes(z.read(name))
            elif '.dist-info/' in name and 'license' in name.lower():
                (licenses/('upscale-ncnn-'+Path(name).name)).write_bytes(z.read(name))
    (vendor/'__init__.py').write_text('# Native inference module; imported directly.\n',encoding='utf8')
    model=download(data['model']['url'],data['model']['sha256'])
    target=HERE/'model';target.mkdir(exist_ok=True)
    names={'2x_OpenProteus_Compact_i2_70K.bin','2x_OpenProteus_Compact_i2_70K.param'}
    with tarfile.open(model,'r:gz') as tar:
        found=set()
        for member in tar.getmembers():
            name=Path(member.name).name
            if member.isfile() and name in names:
                (target/name).write_bytes(tar.extractfile(member).read());found.add(name)
        if found!=names:
            raise ValueError('Model archive does not contain expected NCNN files')
    license_data=urlopen(data['license']['url'],timeout=30).read()
    if hashlib.sha256(license_data).hexdigest()!=data['license']['sha256']:
        raise ValueError('Model license changed; review before updating the pinned manifest')
    (licenses/'OpenProteus-CC-BY-NC-4.0.txt').write_bytes(license_data)
    (licenses/'OpenProteus-NOTICE.txt').write_text(
        'OpenProteus Compact by SiroSky. CC BY-NC 4.0.\n'
        'Original: https://github.com/Sirosky/Upscale-Hub/releases/tag/OpenProteus\n'
        'NCNN conversion obtained from TNTwise/real-video-enhancer-models.\n'
        'Weights are independent of the application license; noncommercial restriction applies.\n',encoding='utf8')
    print('Verified upstream inference wrapper, OpenProteus weights and model license.')

if __name__=='__main__':
    main()
