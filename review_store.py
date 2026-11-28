"""Append-only visual review records; OCR observations are immutable evidence."""
import csv
from contextlib import closing
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
import uuid


def csv_value(value):
    """Export untrusted text as text, without changing SQLite or JSON evidence."""
    if isinstance(value,str) and (value.startswith(('\t','\r','\n')) or value.lstrip(' \t\r\n').startswith(('=','+','-','@'))):
        return "'"+value
    return value

def ensure_schema(db):
    db.executescript('''
    CREATE TABLE IF NOT EXISTS ocr_reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        video INTEGER NOT NULL, second REAL NOT NULL, camera_date TEXT NOT NULL,
        previous_id INTEGER NOT NULL DEFAULT 0,
        decision TEXT NOT NULL, confirmed_date TEXT,
        boundary_second REAL, uncertainty_second REAL,
        provider TEXT NOT NULL, model TEXT, evidence TEXT NOT NULL,
        created TEXT NOT NULL,
        UNIQUE(video,second,camera_date,previous_id)
    );
    CREATE VIEW IF NOT EXISTS ocr_latest_reviews AS
      SELECT r.* FROM ocr_reviews r WHERE r.id=(
        SELECT MAX(n.id) FROM ocr_reviews n WHERE
        n.video=r.video AND n.second=r.second AND n.camera_date=r.camera_date);
    ''')

def latest(db, video, second, camera_date):
    row=db.execute('SELECT * FROM ocr_latest_reviews WHERE video=? AND second=? AND camera_date=?',
                   (video,second,camera_date)).fetchone()
    if not row:
        return None
    keys=[x[1] for x in db.execute('PRAGMA table_info(ocr_reviews)')]
    return dict(zip(keys,row))

def submit(database, video_id, second, camera_date, expected_review_id, decision,
           provider, evidence, model=None, confirmed_date=None, boundary_second=None,
           uncertainty_second=None):
    database=Path(database).expanduser().resolve()
    if not database.is_file():
        raise ValueError('OCR database does not exist; run OCR first.')
    if decision not in ('verified','corrected','uncertain','rejected'):
        raise ValueError('decision must be verified, corrected, uncertain or rejected')
    if not provider.strip() or not evidence.strip():
        raise ValueError('Provider and visual evidence are required.')
    if len(evidence)>12000 or len(provider)>200 or (model and len(model)>200):
        raise ValueError('Review text is too long.')
    date.fromisoformat(camera_date)
    if confirmed_date:
        date.fromisoformat(confirmed_date)
    if decision in ('verified','corrected') and not confirmed_date:
        raise ValueError('Verified/corrected reviews require confirmed_date.')
    if decision=='verified' and confirmed_date!=camera_date:
        raise ValueError('Use corrected when changing the camera date.')
    if decision=='corrected' and confirmed_date==camera_date:
        raise ValueError('Use verified when confirming the camera date.')
    if decision in ('uncertain','rejected') and confirmed_date:
        raise ValueError('Uncertain/rejected observations cannot claim a confirmed date.')
    for number in (second,boundary_second,uncertainty_second):
        if number is not None and (not math.isfinite(number) or number<0):
            raise ValueError('Timestamps and uncertainty must be finite and nonnegative.')
    if boundary_second is not None and uncertainty_second is None:
        raise ValueError('A boundary requires uncertainty_second; do not invent precision.')
    with closing(sqlite3.connect(database, timeout=5)) as db:
        for name in ('ocr_videos','ocr_stamps','ocr_scans'):
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone():
                raise ValueError('Not a VHS Studio OCR database.')
        ensure_schema(db)
        db.execute('BEGIN IMMEDIATE')
        source=db.execute('SELECT path,size,mtime_ns FROM ocr_videos WHERE id=?',(video_id,)).fetchone()
        if not source or not db.execute('SELECT 1 FROM ocr_stamps WHERE video=? AND second=? AND date=?',
                                       (video_id,second,camera_date)).fetchone():
            raise ValueError('Unknown OCR finding. Read the latest export first.')
        stat=Path(source[0]).stat()
        if (stat.st_size,stat.st_mtime_ns)!=(source[1],source[2]):
            raise ValueError('The video has changed since OCR; do not review stale findings.')
        if boundary_second is not None:
            from engine import probe
            if boundary_second>probe(source[0])['seconds']:
                raise ValueError('Boundary is outside this video timeline.')
        previous=latest(db,video_id,second,camera_date)
        current_id=previous['id'] if previous else 0
        if expected_review_id!=current_id:
            raise ValueError(f'Review conflict: latest review id is {current_id}. Reload before writing.')
        cursor=db.execute('''INSERT INTO ocr_reviews
          (video,second,camera_date,previous_id,decision,confirmed_date,boundary_second,
           uncertainty_second,provider,model,evidence,created)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
          (video_id,second,camera_date,current_id,decision,confirmed_date,boundary_second,
           uncertainty_second,provider.strip(),model.strip() if model else None,evidence.strip(),
           datetime.now(timezone.utc).isoformat()))
        review_id=cursor.lastrowid
        db.commit()
    # SQLite is authoritative even if a spreadsheet has locked the CSV export.
    try:
        with closing(sqlite3.connect(database)) as db:
            export(db,database.parent)
        return dict(review_id=review_id,saved=True,exports_updated=True)
    except (OSError, sqlite3.Error) as error:
        return dict(review_id=review_id,saved=True,exports_updated=False,warning=str(error))

def export(db, directory):
    """Consistent snapshot including raw findings, latest review and full history."""
    ensure_schema(db)
    directory=Path(directory)
    # Serialize independent exporters and OCR writers using a brief DB lock.
    # Atomic rename per export; consumers needing cross-file consistency use DB.
    with db:
        db.execute('BEGIN IMMEDIATE')
        videos=[]; csvrows=[]
        for video,path,size,mtime in db.execute('SELECT id,path,size,mtime_ns FROM ocr_videos ORDER BY path'):
            hits=[]
            for second,stamp,raw in db.execute('SELECT second,date,raw FROM ocr_stamps WHERE video=? ORDER BY second,date',(video,)):
                review=latest(db,video,second,stamp)
                hit=dict(second=second,date=stamp,raw=raw,review=review)
                hits.append(hit)
                r=review or {}
                csvrows.append([video,path,second,stamp,raw,*[r.get(k) for k in
                    ('id','decision','confirmed_date','boundary_second','uncertainty_second','provider','model','evidence','created')]])
            scans=[dict(fps=fps,done=bool(done)) for fps,done in db.execute('SELECT fps,done FROM ocr_scans WHERE video=?',(video,))]
            keys=[x[1] for x in db.execute('PRAGMA table_info(ocr_reviews)')]
            history=[dict(zip(keys,row)) for row in db.execute('SELECT * FROM ocr_reviews WHERE video=? ORDER BY id',(video,))]
            import re
            name=Path(path).name
            videos.append(dict(id=video,path=path,size=size,mtime_ns=mtime,
                expected_date=name[:10] if re.match(r'\d{4}-\d\d-\d\d',name) else None,
                scans=scans,hits=hits,review_history=history))
        generation=uuid.uuid4().hex
        data=dict(format='VHS Studio OCR',version=2,generation=generation,
            created=datetime.now(timezone.utc).isoformat(),videos=videos)
        files=[]
        try:
            for suffix in ('json','csv'):
                tmp=directory/f'.OCR-Fundstellen-{generation}.{suffix}.tmp'
                files.append(tmp)
                if suffix=='json':
                    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
                else:
                    with tmp.open('w',encoding='utf-8-sig',newline='') as handle:
                        writer=csv.writer(handle,delimiter=';')
                        writer.writerow(['video_id','video_path','second','camera_date','raw_text','review_id','decision',
                            'confirmed_date','boundary_second','uncertainty_second','provider','model','evidence','reviewed_at'])
                        writer.writerows([csv_value(value) for value in row] for row in csvrows)
                tmp.replace(directory/f'OCR-Fundstellen.{suffix}')
        finally:
            for tmp in files:
                tmp.unlink(missing_ok=True)
