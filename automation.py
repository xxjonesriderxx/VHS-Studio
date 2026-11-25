"""Self-describing local automation entry point; no GUI or network required."""
import json
import os
from pathlib import Path
import sys

GUIDE = """VHS Studio local automation / Lokale KI-Steuerung
Use --describe to read this guide and --api REQUEST.json RESPONSE.json for calls.
Request: {"tool":"get_options","arguments":{}}. Read the response JSON;
ok=false means failure. Paths are local absolute paths. No cloud upload.
1. get_options: read option schema and detected hardware.
2. scan_folder(source, output, options): read-only asynchronous scan; returns id.
3. get_job_status(job_id): poll until running=false; inspect completion.jobs,
   errors and selected operations. A plan is not a completed video render.
4. start_processing(scan_id): writes outputs. Only invoke for user-authorized
   processing after reviewing the scan. Returns a NEW processing job id.
5. read_job_logs(job_id,cursor=0,limit=100): reuse next_cursor for live logs.
6. get_job_status: inspect per-video results, completion and failures, not only
   process exit. cancel_job(job_id) requests safe cooperative cancellation.
7. read_ocr(job_id,language='de'|'en'): JSON/CSV/SQLite paths and review prompt.
   OCR is a clue, not verified truth. Inspect original frames before proposing
   cuts. This app does not automatically split footage from OCR results.
list_jobs(limit=20) lists persistent API/MCP jobs across server restarts.
submit_ocr_review(database,video_id,second,camera_date,expected_review_id,
decision,provider,evidence,model=None,confirmed_date=None,boundary_second=None,
uncertainty_second=None) appends a visual review and regenerates JSON/CSV.
Read exact finding keys and latest review.id from JSON; use 0 if unreviewed.
Never replace raw OCR with guesses. Model/provider are self-reported; unknown
model must be null. Boundaries refer to this video's timeline and require
uncertainty in seconds. Preserve history; conflicting revisions are rejected.
Export mode preserves sources; archive mode moves prior versions after
verification. Never enable archive mode without authorization. Existing locks
prevent concurrent writes to the same output/archive. GUI jobs are currently
separate: API/MCP cannot cancel or attach to a running GUI job.
CPU modes gentle/balanced/full/background adapt to detected physical cores.
background uses Idle priority, up to 2 cores and paced GPU frame processing.
GPU pacing inserts idle time, not a driver-enforced percentage or gaming FPS
guarantee. cpu_cores can override the automatic CPU count; omit for defaults.
MCP: launch this executable with --mcp using an MCP client over stdio.
There is no network listener or automatic registration into AI clients.
Discovery hint: %LOCALAPPDATA%/VHS Studio/instances/*.json records GUI PIDs,
launch commands and this guide. Verify PID and process creation time before
using a record; crashed instances can leave stale descriptors.
"""

def describe():
    from mcp_server import serve
    from app_version import VERSION
    return dict(name='VHS Studio', version=VERSION, guide=GUIDE,
                capabilities=serve(request={'tool':'get_options','arguments':{}}))

def command_line():
    from mcp_server import reconnect_stdio, serve
    if '--describe' in sys.argv:
        reconnect_stdio()
        print(json.dumps(describe(), ensure_ascii=False, indent=2))
        return
    i = sys.argv.index('--api')
    if len(sys.argv) != i + 3:
        raise ValueError('Usage: --api REQUEST.json RESPONSE.json')
    request, response = map(Path, sys.argv[i+1:i+3])
    if request.resolve() == response.resolve():
        raise ValueError('Request and response must be different files.')
    try:
        result = dict(ok=True, result=serve(request=json.loads(request.read_text('utf-8-sig'))))
    except Exception as error:
        result = dict(ok=False, error=str(error), type=type(error).__name__)
    response.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    if not result['ok']:
        raise SystemExit(1)

def register_instance():
    import psutil
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home()))/'VHS Studio'/'instances'
    folder.mkdir(parents=True, exist_ok=True)
    command = [sys.executable]
    if not getattr(sys, 'frozen', False):
        command.append(str(Path(__file__).with_name('app.py')))
    record = folder/f'{os.getpid()}.json'
    record.write_text(json.dumps(dict(pid=os.getpid(), process_time=psutil.Process().create_time(),
        command=command, pythonpath=os.environ.get('PYTHONPATH', ''), guide=GUIDE), indent=2), encoding='utf8')
    import atexit
    atexit.register(lambda: record.unlink(missing_ok=True))
