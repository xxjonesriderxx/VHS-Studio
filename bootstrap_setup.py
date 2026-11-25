"""Install original, hash-locked wheels into this user's private app environment."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import venv


def main():
    root=Path(__file__).resolve().parent
    lock=json.loads((root/'bootstrap-lock.json').read_text('utf8'))
    requirements=root/'bootstrap-requirements.txt'
    checksum=hashlib.sha256(requirements.read_bytes()).hexdigest()
    if checksum!=lock['requirements_sha256']:
        raise ValueError('The original dependency lock was changed. Download VHS Studio again.')
    env=root/'.venv'
    interpreter=env/'Scripts/python.exe'
    marker=root/'.bootstrap-ready'
    if marker.is_file() and marker.read_text('ascii').strip()==checksum and interpreter.is_file():
        return
    print('Preparing a private Python environment / Private Python-Umgebung vorbereiten',flush=True)
    if not interpreter.is_file():
        venv.EnvBuilder(with_pip=True,system_site_packages=False).create(env)
    process_env=dict(os.environ,PYTHONNOUSERSITE='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
    for key in ('PYTHONPATH','PYTHONHOME'):
        process_env.pop(key,None)
    subprocess.run([str(interpreter),'-I','-m','pip','--isolated','install',
        '--disable-pip-version-check','--no-input','--no-deps','--only-binary=:all:',
        '--require-hashes','-r',str(requirements)],env=process_env,check=True)
    subprocess.run([str(interpreter),'-I','-m','pip','--isolated','check'],env=process_env,check=True)
    # Do not import the upstream wrapper facade: it pulls in unused cv2/sympy.
    subprocess.run([str(interpreter),'-I','-c',
        'import tkinter,customtkinter,PIL,mcp,psutil,numpy,scipy,vsdeinterlace; '
        'import winrt.windows.media.ocr; print("Application dependencies ready")'],env=process_env,check=True)
    marker.write_text(checksum+'\n',encoding='ascii')


if __name__=='__main__':
    main()
