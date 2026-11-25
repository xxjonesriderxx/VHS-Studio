"""Build the two Windows release variants. Does not publish or alter Git."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from app_version import VERSION
ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    from app_updates import version_key
    year,month,day,build=version_key(VERSION)
    import re
    version_file=ROOT/'version.txt'
    text=version_file.read_text('utf8')
    text=re.sub(r'filevers=\([^)]*\),prodvers=\([^)]*\)',
                f'filevers=({year},{month},{day},{build}),prodvers=({year},{month},{day},{build})',text)
    text=re.sub(r"StringStruct\('(FileVersion|ProductVersion)','[^']*'\)",
                lambda m:f"StringStruct('{m[1]}','{VERSION}')",text)
    version_file.write_text(text,encoding='utf8')
    subprocess.run([sys.executable,'prepare_hybrid.py'],check=True)
    subprocess.run([sys.executable,'prepare_embedded.py'],check=True)
    subprocess.run([sys.executable,'icon.py'],check=True)
    subprocess.run([sys.executable,'-m','PyInstaller','VHSStudio-hybrid.spec','--noconfirm',
        '--distpath','hybrid-dist','--workpath','hybrid-build'],check=True)
    stage=ROOT/'hybrid-stage'
    exe=ROOT/'hybrid-dist/VHS Studio.exe'
    shutil.copy2(exe,stage/'VHS Studio.exe')
    for name in ('README.md','LICENSE','THIRD-PARTY-NOTICES.md','AI-CONTROL.md',
                 'runtime-manifest.json','embedded-manifest.json','requirements-build.txt'):
        source=ROOT/name
        if source.exists():
            shutil.copy2(source,stage/name)
    # Only this release's components; previous builds never leak into the ZIP.
    output=ROOT/'dist';output.mkdir(exist_ok=True)
    standalone=output/f'VHS-Studio-{VERSION}.exe'
    shutil.copy2(exe,standalone)
    archive=output/f'VHS-Studio-{VERSION}-portable.zip'
    files=[p for p in stage.iterdir() if p.is_file()]
    component_root=stage/'components'/VERSION
    files+=list(component_root.rglob('*'))
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in files:
            if path.is_file():
                z.write(path,Path('VHS Studio')/path.relative_to(stage))
    import hashlib
    sums={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in (standalone,archive)}
    (output/'release-checksums.json').write_text(json.dumps(sums,indent=2),encoding='utf8')
    print(json.dumps(dict(version=VERSION,assets=[str(standalone),str(archive)],sha256=sums),indent=2))

if __name__=='__main__':
    main()
