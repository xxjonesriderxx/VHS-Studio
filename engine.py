"""VHS Studio processing engine."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from fractions import Fraction
from contextlib import closing
import runtime_components as runtime
import archive_layout

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
FFMPEG = runtime.asset('media','bin/ffmpeg.exe')
FFPROBE = runtime.asset('media','bin/ffprobe.exe')
EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".mpg", ".mpeg", ".vob", ".mts", ".m2ts", ".dv"}
EXCLUDED = archive_layout.EXCLUDED | {"_Autostart-Transfer", "$RECYCLE.BIN", "System Volume Information"}
STAGE = re.compile(r" - (Original|Deinterlaced(?: QTGMC| BWDIF)?|OpenProteus)$", re.I)
EVENTS = None
STOP_FILE = None
OCR_RATE = 1.0
BACKGROUND_GPU = False

def check_cancel():
    if STOP_FILE and STOP_FILE.exists():
        raise InterruptedError("Vom Benutzer abgebrochen.")

def emit(event, **values):
    if EVENTS:
        EVENTS.write(json.dumps({"event": event, **values}, ensure_ascii=False) + "\n")
        EVENTS.flush()

def command(args, **kwargs):
    result = subprocess.run(list(map(str, args)), capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf8", errors="replace")[-2500:] or "Prozess wurde beendet.")
    return result

def probe(path):
    global FFMPEG, FFPROBE
    runtime.ensure('media')
    FFMPEG=runtime.asset('media','bin/ffmpeg.exe')
    FFPROBE=runtime.asset('media','bin/ffprobe.exe')
    data = json.loads(command([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", path], timeout=45).stdout)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if not video:
        raise ValueError("Keine Videospur gefunden.")
    data["video"] = video
    data["seconds"] = float(data["format"].get("duration", video.get("duration", 0)))
    if data["seconds"] <= 0:
        raise ValueError("Videolänge konnte nicht ermittelt werden.")
    data["interlaced"] = video.get("field_order", "unknown") != "progressive"
    return data

def identity(path):
    s = path.stat()
    return s.st_size, s.st_mtime_ns

def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def discover(cfg):
    source = Path(cfg["source"]).resolve()
    output = Path(cfg["output"]).resolve()
    jobs, errors = [], []
    for folder, directories, names in os.walk(source):
        check_cancel()
        directories[:] = sorted(d for d in directories if d not in EXCLUDED and not d.startswith(".vhs-"))
        if output != source:
            directories[:] = [d for d in directories if not (Path(folder) / d).resolve().is_relative_to(output)]
        if not cfg["recursive"]:
            directories[:] = []
        for name in sorted(names):
            path = Path(folder) / name
            if path.suffix.lower() not in EXTENSIONS:
                continue
            processed = bool(re.search(r" - (Deinterlaced|OpenProteus)", path.stem))
            try:
                info = probe(path)
                actions, actual, replacement = [], path, False
                if cfg["replace"] and " - Deinterlaced" in path.stem:
                    comment = info["format"].get("tags", {}).get("comment", "")
                    if "QTGMC" not in comment and ("BWDIF" in comment or not comment):
                        old = archive_layout.original(source,path.relative_to(source),STAGE.sub('',path.stem))
                        if old and probe(old)["interlaced"]:
                            actual, replacement = old, True
                            actions.append("QTGMC-Austausch")
                if cfg["deinterlace"] and not processed:
                    actions.append("Deinterlacing" if info["interlaced"] else "MP4 erstellen")
                if cfg["upscale"] and "OpenProteus" not in path.stem:
                    if info["interlaced"] and not actions:
                        errors.append(f"{name}: Vor dem Upscaling Deinterlacing aktivieren.")
                        continue
                    actions.append("OpenProteus 2×")
                if cfg["ocr"]:
                    actions.append("Datums-OCR")
                if not actions:
                    continue
                jobs.append(dict(path=str(path), input=str(actual), relative=str(path.relative_to(source)), name=name,
                                 seconds=info["seconds"], action=" → ".join(actions), replace=replacement))
                emit("scan", count=len(jobs), name=name)
            except Exception as exc:
                errors.append(f"{name}: {exc}")
    jobs.sort(key=lambda j: (bool(j["replace"]), Path(j["path"]).stat().st_size if j["replace"] else j["name"]))
    return (jobs[:cfg["limit"]] if cfg["limit"] else jobs), errors

def encode_options(comment=""):
    args = ["-c:v", "libx265", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart"]
    return args + (["-metadata", "comment=" + comment] if comment else [])

def run_encoder(args, seconds, label):
    with tempfile.TemporaryFile() as error:
        with subprocess.Popen([str(FFMPEG), "-n", "-nostdin", "-v", "warning", "-progress", "pipe:1", *map(str,args)],
                              stdout=subprocess.PIPE, stderr=error, creationflags=subprocess.CREATE_NO_WINDOW) as proc:
            for line in iter(proc.stdout.readline, b""):
                if STOP_FILE and STOP_FILE.exists():
                    proc.kill()
                    proc.wait()
                    raise InterruptedError("Vom Benutzer abgebrochen.")
                if line.startswith(b"out_time_us="):
                    try:
                        emit("progress", progress=min(1, int(line.split(b"=")[1]) / 1e6 / seconds), label=label)
                    except ValueError:
                        pass
            if proc.wait():
                error.seek(0)
                raise RuntimeError(error.read().decode(errors="replace")[-2500:])

def qtgmc(source, target, info):
    native=runtime.activate_qtgmc()
    import vapoursynth as vs
    core = vs.core
    plugins = native / "vapoursynth/plugins" if runtime.manifest() else ROOT / "vapoursynth/plugins"
    if plugins.exists():
        for dll in sorted(plugins.rglob("*.dll")):
            try:
                core.std.LoadPlugin(path=str(dll))
            except vs.Error:
                pass
    from vsdeinterlace import QTempGaussMC
    import psutil
    core.num_threads = len(psutil.Process().cpu_affinity())
    original = core.bs.VideoSource(source=str(source), cachemode=0)
    props = original.get_frame(0).props
    order = props.get("_FieldBased", 0)
    if order not in (1,2):
        order = 1 if info["video"].get("field_order") in ("bb","bt") else 2
    clip = QTempGaussMC().deinterlace(original.std.SetFrameProps(_FieldBased=order))
    sar = info["video"].get("sample_aspect_ratio", "1:1").replace(":", "/")
    if sar in ("0/1","N/A"):
        sar = "1/1"
    colors=[]
    for prop, option in (("_Matrix","-colorspace"),("_Primaries","-color_primaries"),("_Transfer","-color_trc")):
        if prop in props and int(props[prop]) != 2:
            colors.extend([option,str(int(props[prop]))])
    if "_Range" in props:
        colors.extend(["-color_range","tv" if props["_Range"]==vs.RANGE_LIMITED else "pc"])
    args = [str(FFMPEG), "-n", "-nostdin", "-v", "warning", "-f", "yuv4mpegpipe", "-i", "pipe:0", "-i", str(source),
            "-map", "0:v", "-map", "1:a?", "-vf", f"setsar={sar}", *colors, *encode_options("Deinterlacing: QTGMC (QTempGaussMC defaults)"), str(target)]
    with tempfile.TemporaryFile() as error:
        with subprocess.Popen(args, stdin=subprocess.PIPE, stderr=error, creationflags=subprocess.CREATE_NO_WINDOW) as proc:
            try:
                def progress(n, total):
                    check_cancel()
                    if n % 50 == 0:
                        emit("progress", progress=n / total, label="QTGMC · Halbbilder rekonstruieren")
                clip.output(proc.stdin, y4m=True, progress_update=progress)
                proc.stdin.close()
                if proc.wait():
                    error.seek(0)
                    raise RuntimeError(error.read().decode(errors="replace")[-2500:])
            except BaseException:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                raise

def upscale(source, target, info):
    from inference_backend import load
    wrapped=load()
    video = info["video"]
    sar = Fraction(video.get("sample_aspect_ratio", "1:1").replace(":", "/"))
    width, height = round(video["width"] * sar / 2) * 2, video["height"]
    fps = Fraction(video["avg_frame_rate"])
    model = runtime.asset('openproteus','model/2x_OpenProteus_Compact_i2_70K')
    net = wrapped.UPSCALEWrapped(0, False, 2)
    net.set_parameters(128, 2)
    net.load(str(model)+".param", str(model)+".bin")
    decoder_args = [str(FFMPEG), "-v", "error", "-i", str(source), "-map", "0:v", "-vf", f"scale={width}:{height},setsar=1",
                    "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    encoder_args = [str(FFMPEG), "-n", "-nostdin", "-v", "warning", "-f", "rawvideo", "-pixel_format", "rgb24",
                    "-video_size", f"{width*2}x{height*2}", "-framerate", str(fps), "-i", "pipe:0", "-i", str(source),
                    "-map", "0:v", "-map", "1:a?", "-vf", "setsar=1",
                    *encode_options(info["format"].get("tags",{}).get("comment","")), str(target)]
    with tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as decerr:
        with subprocess.Popen(decoder_args, stdout=subprocess.PIPE, stderr=decerr, creationflags=subprocess.CREATE_NO_WINDOW) as dec:
            with subprocess.Popen(encoder_args, stdin=subprocess.PIPE, stderr=err, creationflags=subprocess.CREATE_NO_WINDOW) as enc:
                try:
                    size, count = width*height*3, 0
                    while True:
                        check_cancel()
                        data = dec.stdout.read(size)
                        if not data:
                            break
                        if len(data) != size:
                            raise ValueError("Unvollständiges Videobild.")
                        incoming = wrapped.UPSCALEImage(data,width,height,3)
                        outgoing = wrapped.UPSCALEImage(bytes(size*4),width*2,height*2,3)
                        started = time.monotonic()
                        net.process(incoming,outgoing)
                        if BACKGROUND_GPU:
                            # Pace submission, not a GPU utilization guarantee.
                            remaining = (time.monotonic() - started) * 3
                            while remaining > 0:
                                check_cancel()
                                pause = min(.1, remaining)
                                time.sleep(pause)
                                remaining -= pause
                        enc.stdin.write(outgoing.get_data())
                        count += 1
                        if count % 10 == 0:
                            emit("progress",progress=min(1,count/float(fps)/info["seconds"]),label="OpenProteus · Details aufarbeiten")
                    enc.stdin.close()
                    if dec.wait() or enc.wait():
                        err.seek(0); decerr.seek(0)
                        raise RuntimeError((err.read()+decerr.read()).decode(errors="replace")[-2500:])
                finally:
                    for proc in (dec,enc):
                        if proc.poll() is None:
                            proc.kill()
                            proc.wait()

def validate(info, target, factor=1):
    out = probe(target)
    if abs(out["seconds"]-info["seconds"]) > max(.6, info["seconds"]*.001):
        raise ValueError("Ausgabe und Quelle haben unterschiedliche Längen.")
    if factor == 1 and (out["video"]["width"],out["video"]["height"]) != (info["video"]["width"],info["video"]["height"]):
        raise ValueError("Unerwartete Bildgröße.")
    if factor == 2 and out["video"]["height"] != info["video"]["height"]*2:
        raise ValueError("Unerwartete Upscale-Bildgröße.")
    if any(s["codec_type"]=="audio" for s in info["streams"]) and not any(s["codec_type"]=="audio" for s in out["streams"]):
        raise ValueError("Die Tonspur fehlt.")
    for point in (0,max(0,out["seconds"]-1.5)):
        command([FFMPEG,"-v","error","-xerror","-ss",point,"-i",target,"-t",1.5,"-f","null","NUL"])
    return out

def publish(transfers, guards, logdir):
    for path,state in guards:
        if identity(path) != state:
            raise RuntimeError(f"Quelle wurde während der Bearbeitung geändert: {path}")
    for prepared,target,backup in transfers:
        if backup and backup.exists():
            raise FileExistsError(f"Sicherung existiert: {backup}")
        if not backup and target.exists():
            raise FileExistsError(f"Ausgabe existiert: {target}")
    journal = logdir / ("Uebergabe-"+uuid.uuid4().hex+".json")
    journal.write_text(json.dumps([{"prepared":str(a),"target":str(b),"backup":str(c) if c else None}
                                   for a,b,c in transfers],ensure_ascii=False),encoding="utf8")
    moves, installed = [], []
    try:
        for prepared,target,backup in transfers:
            target.parent.mkdir(parents=True,exist_ok=True)
            if backup:
                backup.parent.mkdir(parents=True,exist_ok=True)
                target.rename(backup)
                moves.append((backup,target))
            prepared.rename(target)
            installed.append((target,prepared))
        journal.unlink()
    except BaseException:
        for target,prepared in reversed(installed):
            target.rename(prepared)
        for backup,target in reversed(moves):
            backup.rename(target)
        raise

async def ocr_scan(path, info, db):
    from datetime import date
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter
    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        raise RuntimeError("Windows-Texterkennung ist nicht verfügbar. Windows-Sprachpakete prüfen.")
    size,mtime = identity(path)
    db.execute("INSERT OR IGNORE INTO ocr_videos(path,size,mtime_ns,next_second,done) VALUES (?,?,?,0,0)",(str(path),size,mtime))
    video = db.execute("SELECT id FROM ocr_videos WHERE path=? AND size=? AND mtime_ns=?",(str(path),size,mtime)).fetchone()[0]
    rate = OCR_RATE
    db.execute("CREATE TABLE IF NOT EXISTS ocr_scans(video INTEGER,fps REAL,next_sample INTEGER DEFAULT 0,done INTEGER DEFAULT 0,PRIMARY KEY(video,fps))")
    db.execute("INSERT OR IGNORE INTO ocr_scans(video,fps) VALUES (?,?)",(video,rate))
    start,done = db.execute("SELECT next_sample,done FROM ocr_scans WHERE video=? AND fps=?",(video,rate)).fetchone()
    if done:
        return
    import math
    pattern = re.compile(r"(?<!\d)(\d{1,2})[ .:/,-]+(\d{1,2})[ .:/,-]+((?:19|20)\d{2})(?!\d)")
    frame_size = 900*412
    total = math.ceil(info["seconds"]*rate)
    batch = max(1,int(10*rate))
    for sample in range(start,total,batch):
        check_cancel()
        count = min(batch,total-sample)
        second = sample/rate
        data = command([FFMPEG,"-v","error","-ss",second,"-i",path,"-filter_complex",
                        f"fps={rate}:start_time=0,scale=900:676,format=gray,split[a][b];[a]crop=900:206:0:0[t];[b]crop=900:206:0:470[u];[t][u]vstack",
                        "-frames:v",count,"-an","-pix_fmt","gray","-f","rawvideo","-"],timeout=120).stdout
        if len(data)%frame_size:
            raise ValueError("Unvollständiges OCR-Bild.")
        for i in range(0,len(data),frame_size):
            writer = DataWriter()
            writer.write_bytes(data[i:i+frame_size])
            bitmap = SoftwareBitmap.create_copy_from_buffer(writer.detach_buffer(),BitmapPixelFormat.GRAY8,900,412)
            try:
                result = await engine.recognize_async(bitmap)
                for line in result.lines:
                    for day,month,year in pattern.findall(line.text):
                        try:
                            value = date(int(year),int(month),int(day))
                        except ValueError:
                            continue
                        if value<=date.today():
                            timestamp = round((sample+i//frame_size)/rate,6)
                            db.execute("INSERT OR IGNORE INTO ocr_stamps VALUES (?,?,?,?)",(video,timestamp,value.isoformat(),line.text))
            finally:
                bitmap.close()
        db.execute("UPDATE ocr_scans SET next_sample=? WHERE video=? AND fps=?",(sample+count,video,rate))
        db.execute("UPDATE ocr_videos SET next_second=? WHERE id=?",((sample+count)/rate,video))
        db.commit()
        emit("progress",progress=min(1,(sample+count)/total),label="OCR · Datumsstempel lesen")
    db.execute("UPDATE ocr_scans SET done=1 WHERE video=? AND fps=?",(video,rate))
    db.execute("UPDATE ocr_videos SET done=1 WHERE id=?",(video,))
    db.commit()


def export_ocr(db,logdir):
    from review_store import export
    return export(db,logdir)


def process_job(cfg,job,logdir,db):
    output = Path(cfg["output"]).resolve()
    path,actual = Path(job["path"]),Path(job["input"])
    info = probe(actual)
    guards = [(actual,identity(actual))]
    if actual!=path:
        guards.append((path,identity(path)))
    relative = Path(job["relative"])
    stem = STAGE.sub("",path.stem)
    with tempfile.TemporaryDirectory(prefix=".vhs-",dir=output) as directory:
        tmp, current, rendered = Path(directory),actual,[]
        emit("workspace",path=str(tmp))
        deint = job["replace"] or (cfg["deinterlace"] and not re.search(r" - (Deinterlaced|OpenProteus)",path.stem))
        if deint:
            method = "QTGMC" if job["replace"] else cfg["method"]
            target = tmp/(stem+" - Deinterlaced.mp4")
            if info["interlaced"] and method=="QTGMC":
                qtgmc(actual,target,info)
            else:
                filters = ["-vf","bwdif=mode=send_field:parity=auto:deint=all"] if info["interlaced"] else []
                comment = "Deinterlacing: BWDIF (send_field)" if info["interlaced"] else ""
                run_encoder(["-i",actual,"-map","0:v","-map","0:a?",*filters,*encode_options(comment),target],info["seconds"],"VHS · MP4 erstellen")
            validate(info,target)
            rendered.append(("Deinterlaced",target))
            current = target
        if cfg["upscale"] and "OpenProteus" not in path.stem:
            target = tmp/(stem+" - OpenProteus.mp4")
            current_info = probe(current)
            upscale(current,target,current_info)
            validate(current_info,target,2)
            rendered.append(("OpenProteus",target))
            current = target
        if rendered:
            transfers=[]
            for index,(stage,prepared) in enumerate(rendered):
                top = index==len(rendered)-1
                dest = output/relative.parent/prepared.name
                backup=None
                if cfg["archive"]:
                    if not top:
                        dest=archive_layout.folder(output,'deinterlaced')/relative.parent/prepared.name
                    if job["replace"] and stage=="Deinterlaced" and top:
                        dest,backup=path,archive_layout.folder(output,'deinterlaced')/'_BWDIF'/relative
                transfers.append((prepared,dest,backup))
            if cfg["archive"] and job["replace"] and len(rendered)>1:
                transfers.append((path,archive_layout.folder(output,'deinterlaced')/'_BWDIF'/relative,None))
            if cfg["archive"] and not job["replace"]:
                old_stage='deinterlaced' if 'Deinterlaced' in path.stem else 'originals'
                transfers.append((path,archive_layout.folder(output,old_stage)/relative,None))
            check_cancel()
            emit("progress",progress=1,label="Prüfsumme und Ablage")
            hashes=[(dest,sha(prepared)) for prepared,dest,_ in transfers]
            publish(transfers,guards,logdir)
            current=next(dest for prepared,dest,_ in transfers if prepared==current)
            for dest,checksum in hashes:
                if sha(dest)!=checksum:
                    raise RuntimeError(f"Prüfsumme stimmt nicht: {dest}")
            db.execute("INSERT INTO runs VALUES (?,?,?,?,?)",(uuid.uuid4().hex,str(path),str(current),time.strftime("%Y-%m-%d %H:%M:%S"),
                       json.dumps({"actions":job["action"],"files":[{"path":str(p),"sha256":h} for p,h in hashes]},ensure_ascii=False)))
            db.commit()
        if cfg["ocr"]:
            import asyncio
            asyncio.run(ocr_scan(current,probe(current),db))
    return str(current)

def worker(config,event_file):
    global EVENTS, STOP_FILE, OCR_RATE, BACKGROUND_GPU, FFMPEG, FFPROBE
    import psutil
    EVENTS=open(event_file,"a",encoding="utf8",buffering=1)
    cfg=json.loads(Path(config).read_text("utf8"))
    def notify(title_de,title_en,body_de,body_en):
        if not cfg.get('scan_only') and cfg.get('notifications',True):
            from notifications import send
            de=cfg.get('language','en')=='de'
            send(title_de if de else title_en,body_de if de else body_en)
    STOP_FILE=Path(config).parent/"stop"
    OCR_RATE=float(cfg.get("ocr_rate",1.0))
    BACKGROUND_GPU = cfg.get('cpu_mode') == 'background'
    if OCR_RATE not in (.25,.5,1,2,4):
        raise ValueError("Ungültiges OCR-Raster.")
    try:
        notify('VHS Studio · Autostart gestartet' if cfg.get('startup') else 'VHS Studio · Restaurierung gestartet',
               'VHS Studio · Auto-start began' if cfg.get('startup') else 'VHS Studio · Restoration started',
               'Der geplante Videolauf wurde gestartet.','The scheduled video batch has started.')
        def dependency_progress(name,current,total):
            check_cancel()
            emit('progress',progress=current/max(total,1),label=f'Komponenten laden · {name} · {current/1e6:.1f}/{total/1e6:.1f} MB')
        runtime.prepare(cfg,dependency_progress)
        FFMPEG=runtime.asset('media','bin/ffmpeg.exe')
        FFPROBE=runtime.asset('media','bin/ffprobe.exe')
        mode=cfg.get("cpu_mode","gentle" if cfg.get("gentle",True) else "full")
        if mode!="full":
            from qtgmc_limit import limit_cpu
            physical=psutil.cpu_count(logical=False) or 2
            default=min(2,max(1,physical//4)) if mode=="background" else min(4,max(1,physical-2)) if mode=="gentle" else max(1,physical-1)
            limit_cpu(physical_cores=cfg.get("cpu_cores") or default,idle=mode in ("gentle","background"))
        jobs,errors=discover(cfg) if cfg.get("scan_only") else (cfg["jobs"],[])
        if cfg.get("scan_only"):
            emit("plan",jobs=jobs,errors=errors)
            return
        output=Path(cfg["output"]).resolve()
        output.mkdir(parents=True,exist_ok=True)
        if cfg['archive']:
            archive_layout.initialize(output)
        logdir=archive_layout.data_folder(output)
        logdir.mkdir(parents=True,exist_ok=True)
        import msvcrt
        lockpath=Path(cfg["source"])/".bearbeitung.lock" if cfg["archive"] else logdir/".lauf.lock"
        with lockpath.open("a+b") as lock:
            lock.seek(0)
            if not lock.read(1):
                lock.write(bytes([0]));lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:
                raise RuntimeError("Der Ordner wird bereits bearbeitet. Nach Abschluss des laufenden Jobs erneut starten.")
            with closing(sqlite3.connect(logdir/"VHS-Studio.sqlite3")) as db:
                db.executescript("""
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,input TEXT,output TEXT,finished TEXT,details TEXT);
                CREATE TABLE IF NOT EXISTS ocr_videos(id INTEGER PRIMARY KEY,path TEXT,size INTEGER,mtime_ns INTEGER,next_second INTEGER,done INTEGER,UNIQUE(path,size,mtime_ns));
                CREATE TABLE IF NOT EXISTS ocr_stamps(video INTEGER,second REAL,date TEXT,raw TEXT,PRIMARY KEY(video,second,date));
                CREATE TABLE IF NOT EXISTS ocr_scans(video INTEGER,fps REAL,next_sample INTEGER DEFAULT 0,done INTEGER DEFAULT 0,PRIMARY KEY(video,fps));
                """)
                failed=0
                for index,job in enumerate(jobs):
                    if STOP_FILE.exists():
                        emit("cancelled")
                        break
                    emit("job",index=index,total=len(jobs),name=job["name"])
                    try:
                        dest=process_job(cfg,job,logdir,db)
                        emit("result",index=index,status="Fertig",detail=dest)
                    except InterruptedError:
                        emit("result",index=index,status="Abgebrochen",detail="Temporäre Ausgabe verworfen.")
                        emit("cancelled")
                        break
                    except Exception as exc:
                        failed+=1
                        emit("result",index=index,status="Fehler",detail=str(exc))
                if cfg["ocr"]:
                    export_ocr(db,logdir)
                if not STOP_FILE.exists():
                    emit("done",total=len(jobs),failed=failed,output=str(output))
                    notify('VHS Studio · Lauf abgeschlossen','VHS Studio · Batch complete',
                        f'{len(jobs)-failed} erfolgreich, {failed} Fehler. Der geplante Lauf ist beendet.',
                        f'{len(jobs)-failed} successful, {failed} failed. The scheduled batch has finished.')
                else:
                    notify('VHS Studio · Lauf abgebrochen','VHS Studio · Batch cancelled',
                        'Fertige Ergebnisse bleiben erhalten.','Completed outputs have been kept.')
                shutil.copyfile(event_file,logdir/("Lauf-"+time.strftime("%Y%m%d-%H%M%S")+".jsonl"))
    except BaseException as exc:
        emit("fatal",message=str(exc))
        notify('VHS Studio · Lauf fehlgeschlagen','VHS Studio · Batch failed',str(exc),str(exc))
        raise
    finally:
        EVENTS.close()
        EVENTS=None
