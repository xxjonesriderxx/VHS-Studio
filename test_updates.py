"""Date-version and updater integrity/rollback checks using dummy files only."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import app_updates as updates

assert updates.version_key('2026-11-25')<updates.version_key('2026-11-25-2')<updates.version_key('2026-11-26')
for bad in ('v1.0.0','2026-02-30','2026-11','2026-11-25-beta'):
    try:
        updates.version_key(bad)
        raise AssertionError('Invalid release accepted')
    except ValueError:
        pass

blob=b'SYNTHETIC UPDATE, NOT EXECUTABLE'
checksum=hashlib.sha256(blob).hexdigest()
release=dict(draft=False,prerelease=False,tag_name='2026-11-26',assets=[dict(
    name='VHS-Studio-2026-11-26.exe',size=len(blob),digest='sha256:'+checksum,
    browser_download_url='https://github.com/xxjonesriderxx/VHS-Studio/releases/download/2026-11-26/VHS-Studio-2026-11-26.exe')])
class Response(io.BytesIO):
    pass
class Opener:
    def open(self,request,**kwargs):
        return Response(json.dumps(release).encode() if 'api.github.com' in request.full_url else blob)
with tempfile.TemporaryDirectory(prefix='VHS-update-check-') as folder:
    root=Path(folder)
    with patch.dict(os.environ,{'LOCALAPPDATA':str(root)}),patch.object(updates,'opener',return_value=Opener()):
        info=updates.latest();assert info['version']=='2026-11-26'
        staged=updates.stage(info);assert staged.read_bytes()==blob
        original=root/'original.exe';original.write_bytes(b'ORIGINAL DUMMY')
        request=root/'request.json'
        data=dict(target=str(original),old_sha256=updates.digest(original),new_sha256=checksum,restart_args=[])
        request.write_text(json.dumps(data))
        with patch.object(sys,'executable',str(staged)),patch.object(updates.subprocess,'Popen') as launch:
            updates.apply(request)
            launch.assert_called_once()
        assert original.read_bytes()==blob
        assert original.with_name('original.exe.previous').read_bytes()==b'ORIGINAL DUMMY'
        original.write_bytes(b'ORIGINAL DUMMY')
        with patch.object(sys,'executable',str(staged)),patch.object(updates.subprocess,'Popen',side_effect=OSError('simulated launch failure')):
            try:
                updates.apply(request)
                raise AssertionError('Expected launch failure')
            except OSError:
                pass
        assert original.read_bytes()==b'ORIGINAL DUMMY'
        release['assets'][0]['digest']='sha256:'+('0'*64)
        info=updates.latest()
        try:
            updates.stage(info)
            raise AssertionError('Checksum mismatch accepted')
        except ValueError:
            pass
print('PASS: date versions, GitHub release selection, verified staging, replacement and rollback; bad checksums rejected')
