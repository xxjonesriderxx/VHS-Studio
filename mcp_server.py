"""MCP stdio server for the same local restoration engine."""
import ctypes
from ctypes import wintypes
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Literal
import uuid

from app_version import VERSION
JOBS=Path(os.environ.get("LOCALAPPDATA",Path.home()))/"VHS Studio"/"jobs"

def reconnect_stdio():
    """Windowed PyInstaller executables still receive client pipe handles."""
    if sys.stdin is not None and sys.stdout is not None:
        return
    import msvcrt
    kernel=ctypes.WinDLL("kernel32",use_last_error=True)
    kernel.GetStdHandle.argtypes=[wintypes.DWORD]
    kernel.GetStdHandle.restype=wintypes.HANDLE
    for name,number,mode,flags in (("stdin",-10,"rb",os.O_RDONLY),("stdout",-11,"wb",os.O_WRONLY),("stderr",-12,"wb",os.O_WRONLY)):
        if getattr(sys,name) is not None:
            continue
        handle=kernel.GetStdHandle(wintypes.DWORD(number))
        if not handle or handle==ctypes.c_void_p(-1).value:
            if name=="stderr":
                setattr(sys,name,open(os.devnull,"w",encoding="utf8"))
                continue
            raise RuntimeError("MCP requires inherited stdin/stdout pipes.")
        fd=msvcrt.open_osfhandle(int(handle),flags|os.O_BINARY)
        stream=os.fdopen(fd,mode,buffering=0)
        setattr(sys,name,io.TextIOWrapper(stream,encoding="utf8",write_through=True))

def serve(request=None):
    if request is None:
        reconnect_stdio()
    from mcp.server.fastmcp import FastMCP
    from pydantic import BaseModel,ConfigDict,Field
    import psutil
    from review import review_prompt

    class Options(BaseModel):
        model_config=ConfigDict(extra="forbid")
        deinterlace: bool=True
        method: Literal["QTGMC","BWDIF"]="QTGMC"
        replace: bool=False
        upscale: bool=False
        ocr: bool=False
        ocr_rate: Literal[0.25,0.5,1.0,2.0,4.0]=1.0
        recursive: bool=True
        limit: int=Field(default=2,ge=0)
        cpu_mode: Literal["gentle","balanced","full","background"]="gentle"
        cpu_cores: int | None=Field(default=None,ge=1,le=64)
        archive: bool=False
        notifications: bool=True
        language: Literal['de','en']='en'

    mcp=FastMCP("VHS Studio",instructions="Restore digitised VHS recordings locally. Scan first, inspect the plan, then start_processing. Archive mode moves prior versions into archive folders. Export mode preserves inputs. OCR dates are clues and require visual verification. No cloud upload.")

    def location(job_id):
        if not re.fullmatch(r"[a-f0-9]{32}",job_id):
            raise ValueError("Invalid job ID.")
        path=JOBS/job_id
        if not (path/"job.json").exists():
            raise ValueError("Unknown job ID.")
        return path

    def events(folder):
        path=folder/"events.jsonl"
        if not path.exists():
            return []
        result=[]
        for line in path.read_text("utf8").splitlines():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return result

    def launch(cfg,kind):
        job_id=uuid.uuid4().hex
        folder=JOBS/job_id
        folder.mkdir(parents=True)
        config=folder/"config.json"
        config.write_text(json.dumps(cfg,ensure_ascii=False),encoding="utf8")
        event_file=folder/"events.jsonl"
        args=[sys.executable]
        if not getattr(sys,"frozen",False):
            args.append(str(Path(__file__).with_name("app.py")))
        args+=["--worker",str(config),str(event_file)]
        env=dict(os.environ,PYINSTALLER_RESET_ENVIRONMENT="1")
        with (folder/"diagnostic.log").open("wb") as handle:
            proc=subprocess.Popen(args,stdout=handle,stderr=handle,creationflags=subprocess.CREATE_NO_WINDOW,env=env)
        record=dict(id=job_id,kind=kind,pid=proc.pid,process_time=psutil.Process(proc.pid).create_time(),created=time.time(),source=cfg["source"],output=cfg["output"])
        (folder/"job.json").write_text(json.dumps(record),encoding="utf8")
        return record

    @mcp.tool()
    def get_options() -> dict:
        """Return all restoration options, defaults, hardware limits and output formats."""
        import runtime_components
        return dict(version=VERSION,components=runtime_components.status(),options_schema=Options.model_json_schema(),cpu=dict(physical=psutil.cpu_count(logical=False),logical=psutil.cpu_count()),
                    export_formats=["SQLite","JSON","CSV"],mcp_transport="stdio",notes=["QTGMC and FFmpeg are bundled.","OpenProteus 2x requires a Vulkan-capable GPU.","CPU limits do not cap GPU load."])

    @mcp.tool()
    def scan_folder(source: str,output: str,options: dict | None=None) -> dict:
        """Start a read-only asynchronous source scan. Poll get_job_status for its plan."""
        settings=Options.model_validate(options or {}).model_dump(exclude_none=True)
        src=Path(source).expanduser().resolve()
        dst=Path(output).expanduser().resolve()
        if not src.is_dir():
            raise ValueError("Source folder does not exist.")
        if settings["archive"]:
            if src!=dst:
                raise ValueError("Archive mode requires the same source and output folder. Processing initializes missing archive folders in English and preserves existing German folders.")
        elif src==dst:
            raise ValueError("Export destination must differ from source.")
        if not any(settings[x] for x in ("deinterlace","replace","upscale","ocr")):
            raise ValueError("Select at least one operation.")
        return launch(dict(settings,source=str(src),output=str(dst),scan_only=True),"scan")

    @mcp.tool()
    def start_processing(scan_id: str,origin: Literal['manual','autostart']='manual') -> dict:
        """Process a completed scan plan using its selected settings. This writes verified outputs and logs."""
        folder=location(scan_id)
        record=json.loads((folder/"job.json").read_text("utf8"))
        if record["kind"]!="scan":
            raise ValueError("A scan job ID is required.")
        plan=next((e for e in reversed(events(folder)) if e["event"]=="plan"),None)
        if not plan or not plan["jobs"]:
            raise ValueError("The scan is unfinished or has no matching videos.")
        cfg=json.loads((folder/"config.json").read_text("utf8"))
        cfg.update(scan_only=False,jobs=plan["jobs"],startup=origin=='autostart')
        return launch(cfg,"processing")

    @mcp.tool()
    def get_job_status(job_id: str) -> dict:
        """Read live status, progress, per-video results and the scan plan, without UI automation."""
        folder=location(job_id)
        record=json.loads((folder/"job.json").read_text("utf8"))
        data=events(folder)
        try:
            proc=psutil.Process(record["pid"])
            running=abs(proc.create_time()-record["process_time"])<.01 and proc.is_running()
        except psutil.NoSuchProcess:
            running=False
        ending=next((e for e in reversed(data) if e["event"] in ("done","fatal","cancelled","plan")),None)
        return dict(**record,running=running,last=data[-1] if data else None,completion=ending,
                    results=[e for e in data if e["event"]=="result"],
                    progress=next((e for e in reversed(data) if e["event"]=="progress"),None))

    @mcp.tool()
    def read_job_logs(job_id: str,cursor: int=0,limit: int=100) -> dict:
        """Read live events incrementally. Pass next_cursor on the next call."""
        folder=location(job_id)
        data=events(folder)
        cursor=max(0,cursor)
        limit=max(1,min(500,limit))
        return dict(events=data[cursor:cursor+limit],next_cursor=min(len(data),cursor+limit))

    @mcp.tool()
    def cancel_job(job_id: str) -> dict:
        """Request cooperative cancellation. In-flight verified file publication finishes safely."""
        folder=location(job_id)
        (folder/"stop").touch()
        return dict(job_id=job_id,cancellation_requested=True)

    @mcp.tool()
    def list_jobs(limit: int=20) -> list[dict]:
        """List recent local scan and processing jobs."""
        if not JOBS.exists():
            return []
        paths=sorted(JOBS.glob("*/job.json"),key=lambda p:p.stat().st_mtime,reverse=True)[:max(1,min(limit,100))]
        return [json.loads(p.read_text("utf8")) for p in paths]

    @mcp.tool()
    def submit_ocr_review(database: str, video_id: int, second: float, camera_date: str,
                          expected_review_id: int, decision: Literal['verified','corrected','uncertain','rejected'],
                          provider: str, evidence: str, model: str | None=None, confirmed_date: str | None=None,
                          boundary_second: float | None=None, uncertainty_second: float | None=None) -> dict:
        """Append a visual review, preserving raw OCR. Read video id, exact OCR timestamp/date and latest review.id from export first (0 if none). expected_review_id detects concurrent edits. Provider/model are self-reported; use null for unknown model. confirmed_date is ISO YYYY-MM-DD. boundary_second is a proposed scene boundary on THIS video timeline, not OCR sample time; requires uncertainty_second. evidence must explain actual frames examined, frame rate/timebase, uncertainty and rationale. No video cutting. JSON/CSV exports regenerate after saving; history remains in SQLite."""
        from review_store import submit
        return submit(database, video_id, second, camera_date, expected_review_id, decision,
                      provider, evidence, model, confirmed_date, boundary_second, uncertainty_second)

    @mcp.tool()
    def read_ocr(job_id: str,language: Literal["de","en"]="en") -> dict:
        """Return OCR export paths and a frame-by-frame verification prompt for a processing job."""
        folder=location(job_id)
        cfg=json.loads((folder/"config.json").read_text("utf8"))
        from archive_layout import data_folder
        target=data_folder(cfg['output'])
        export=target/"OCR-Fundstellen.json"
        if not export.exists():
            raise ValueError("OCR export is not available yet.")
        return dict(json=str(export),csv=str(target/"OCR-Fundstellen.csv"),sqlite=str(target/"VHS-Studio.sqlite3"),
                    verification_prompt=review_prompt(target,language))

    if request is not None:
        tools = {fn.__name__: fn for fn in (get_options, scan_folder, start_processing,
            get_job_status, read_job_logs, cancel_job, list_jobs, read_ocr, submit_ocr_review)}
        if request.get('tool') not in tools:
            raise ValueError('Unknown tool; call get_options and read --describe.')
        return tools[request['tool']](**request.get('arguments', {}))
    mcp.run(transport="stdio")
