"""Archive compatibility checks, using only generated two-second footage."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
ROOT=Path(__file__).resolve().parent
import site
site.addsitedir(str(ROOT/'builddeps'))
sys.path.insert(0,str(ROOT/'vendor'))
import archive_layout as layout
import engine

with tempfile.TemporaryDirectory(prefix='VHS-archive-check-') as directory:
    for language in ('english','german'):
        root=Path(directory)/language;root.mkdir()
        if language=='german':
            for name in ('_Originalschnitte','_Schnittkorrektur','_Verwaltung','_Deinterlaced'):
                (root/name).mkdir()
        source=root/'2001-01-01 - Original.mkv'
        shutil.copy2(ROOT/'test-source.mkv',source)
        original_sha=hashlib.sha256(source.read_bytes()).hexdigest()
        config=dict(source=str(root),output=str(root),deinterlace=True,method='BWDIF',replace=False,
            upscale=False,ocr=False,ocr_rate=1,recursive=True,limit=1,cpu_mode='gentle',archive=True,notifications=False)
        jobs,errors=engine.discover(config)
        assert len(jobs)==1 and not errors,(jobs,errors)
        # Scanning stays read-only, including a completely fresh archive.
        assert not (root/'_OriginalCuts').exists()
        profile=root/'run.json';events=root/'run.jsonl'
        profile.write_text(json.dumps(dict(config,jobs=jobs,scan_only=False)))
        engine.worker(profile,events)
        results=[json.loads(x) for x in events.read_text('utf8').splitlines()]
        assert results[-1]['event']=='done' and results[-1]['failed']==0,results[-4:]
        expected='_Originalschnitte' if language=='german' else '_OriginalCuts'
        assert (root/expected/source.name).is_file()
        assert hashlib.sha256((root/expected/source.name).read_bytes()).hexdigest()==original_sha
        assert not source.exists()
        assert (root/'2001-01-01 - Deinterlaced.mp4').is_file()
        assert layout.original(root,Path('2001-01-01 - Deinterlaced.mp4'),'2001-01-01')==root/expected/source.name
        assert layout.data_folder(root).parent.name==('_Verwaltung' if language=='german' else '_Administration')
        if language=='german':
            assert not (root/'_OriginalCuts').exists()
        print('PASS:',language,'archive, preserved original checksum, read-only scan, replacement lookup and administration fallback')
