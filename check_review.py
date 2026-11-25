"""Review roundtrip, append-only history, conflict protection and live GUI data."""
import csv
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
ROOT=Path(__file__).resolve().parent
import site
site.addsitedir(str(ROOT/'builddeps'))
sys.path[:0]=[str(ROOT),str(ROOT/'vendor')]
os.environ['PYTHONPATH']=os.pathsep.join(sys.path)
from review_store import submit, export
with tempfile.TemporaryDirectory(prefix='VHS-review-check-') as directory:
    base=Path(directory); folder=base/'_Verwaltung/VHS-Studio';folder.mkdir(parents=True)
    os.environ['VHS_STUDIO_STATE_DIR']=str(base/'state')
    video=base/'sample.mkv';shutil.copyfile(ROOT/'test-source.mkv',video)
    stat=video.stat();database=folder/'VHS-Studio.sqlite3'
    with sqlite3.connect(database) as db:
        db.executescript('''CREATE TABLE ocr_videos(id INTEGER PRIMARY KEY,path TEXT,size INTEGER,mtime_ns INTEGER,next_second INTEGER,done INTEGER);
          CREATE TABLE ocr_stamps(video INTEGER,second REAL,date TEXT,raw TEXT,PRIMARY KEY(video,second,date));
          CREATE TABLE ocr_scans(video INTEGER,fps REAL,next_sample INTEGER,done INTEGER);''')
        db.execute('INSERT INTO ocr_videos VALUES (1,?,?,?,2,1)',(str(video),stat.st_size,stat.st_mtime_ns))
        db.execute("INSERT INTO ocr_stamps VALUES (1,1.0,'2004-09-14','14.09.2004')")
        db.commit();export(db,folder)
    args=dict(database=str(database),video_id=1,second=1,camera_date='2004-09-14',expected_review_id=0,
              decision='verified',confirmed_date='2004-09-14',boundary_second=.4,uncertainty_second=.04,
              provider='Test harness',model=None,evidence='Synthetic fixture; not a real AI assessment.')
    result=submit(**args);assert result['saved'] and result['exports_updated']
    first=result['review_id']
    try:
        submit(**args)
        raise AssertionError('Expected revision conflict')
    except ValueError as error:
        assert 'conflict' in str(error)
    from app import Studio
    ui=Studio();ui.update()
    ui.output.insert(0,str(base));ui.tabs.set(ui.t('Datumsfunde'));ui.load_stamps(False)
    key=ui.stamps.get_children()[0];ui.stamps.selection_set(key)
    assert ui.stamps.set(key,'review')=='Bestätigt'
    from mcp_server import serve
    args.update(expected_review_id=first,decision='corrected',confirmed_date='2005-09-14')
    second=serve(request=dict(tool='submit_ocr_review',arguments=args))
    assert second['saved']
    ui.autosave()  # this is the same periodic callback used for external writes
    assert ui.stamps.set(key,'review')=='Korrigiert'
    assert ui.stamps.set(key,'confirmed')=='2005-09-14'
    assert ui.stamps.selection()==(key,)
    ui.switch_language();ui.load_stamps(False)
    assert ui.stamps.set(key,'review')=='Corrected'
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT COUNT(*) FROM ocr_reviews').fetchone()[0]==2
        assert db.execute('SELECT date,raw FROM ocr_stamps').fetchone()==('2004-09-14','14.09.2004')
    data=json.loads((folder/'OCR-Fundstellen.json').read_text('utf8'))
    assert data['videos'][0]['hits'][0]['review']['confirmed_date']=='2005-09-14'
    assert len(data['videos'][0]['review_history'])==2
    with (folder/'OCR-Fundstellen.csv').open(encoding='utf-8-sig',newline='') as f:
        assert next(csv.DictReader(f,delimiter=';'))['confirmed_date']=='2005-09-14'
    from review import review_prompt
    for language in ('de','en'):
        prompt=review_prompt(folder,language)
        assert 'submit_ocr_review' in prompt and 'expected_review_id' in prompt
        assert str(database) in prompt
    args.update(expected_review_id=second['review_id'],boundary_second=999)
    try:
        submit(**args)
        raise AssertionError('Expected out-of-range failure')
    except ValueError as error:
        assert 'outside' in str(error)
    video.write_bytes(video.read_bytes()+b'changed')
    args.update(boundary_second=None)
    try:
        submit(**args)
        raise AssertionError('Expected changed-video failure')
    except ValueError as error:
        assert 'changed' in str(error)
    for token in ui.tk.call('after','info'):
        ui.tk.call('after','cancel',token)
    ui.destroy()
    db.close()
    import gc
    gc.collect()
    print('PASS: append-only review, MCP/API roundtrip, conflicts, JSON/CSV, live GUI/selection, bilingual prompt, stale/out-of-range rejection')
