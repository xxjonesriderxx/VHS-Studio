"""Package the same own-code launcher and documentation, never a populated cache."""
from pathlib import Path
import zipfile
from app_version import VERSION
from build_bootstrap import sha256

ROOT=Path(__file__).resolve().parent
DOCS=('README.md','LICENSE','AI-CONTROL.md','THIRD-PARTY-NOTICES.md',
      'bootstrap-lock.json','bootstrap-requirements.txt','runtime-manifest.json')


def main():
    output=ROOT/'bootstrap-dist'
    exe=output/f'VHS-Studio-{VERSION}.exe'
    if not exe.is_file():
        raise SystemExit('Build the own-code launcher first.')
    archive=output/f'VHS-Studio-{VERSION}-portable.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as target:
        target.write(exe,'VHS Studio/VHS Studio.exe')
        for name in DOCS:
            target.write(ROOT/name,'VHS Studio/'+name)
    print(exe.name,exe.stat().st_size,sha256(exe))
    print(archive.name,archive.stat().st_size,sha256(archive))


if __name__=='__main__':
    main()
