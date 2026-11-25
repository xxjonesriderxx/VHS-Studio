"""Block publication until evidence and both exact release files are reviewed.

Local preview builds remain possible. A changed/rebuilt executable must be
reviewed again; a prior clearance cannot silently approve different binaries.
"""
import hashlib
import json
from pathlib import Path
import sys

from app_version import VERSION

ROOT = Path(__file__).resolve().parent


def check(record, root=ROOT, status_only=False):
    if record.get('approved') is not True or record.get('version') != VERSION:
        raise ValueError('Redistribution review is unresolved. Do not publish either release asset.')
    evidence = record.get('evidence', [])
    if not evidence or any(not (root / name).is_file() for name in evidence):
        raise ValueError('Redistribution review evidence is missing.')
    expected = {f'VHS-Studio-{VERSION}.exe', f'VHS-Studio-{VERSION}-portable.zip'}
    hashes = record.get('sha256', {})
    if set(hashes) != expected:
        raise ValueError('Both reviewed release assets must be recorded together.')
    if status_only:
        return
    for name, checksum in hashes.items():
        folder=root / record.get('asset_directory','dist')
        if not folder.resolve().is_relative_to(root.resolve()):
            raise ValueError('Release assets must remain inside the project directory.')
        path = folder / name
        if not path.is_file():
            raise ValueError('Reviewed release asset is missing: ' + name)
        with path.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        if digest != checksum:
            raise ValueError('Release asset changed after review: ' + name)


if __name__ == '__main__':
    try:
        with (ROOT / 'release-clearance.json').open(encoding='utf8') as source:
            check(json.load(source), status_only='--status-only' in sys.argv)
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
    print('Both release assets passed the recorded redistribution gate.')
