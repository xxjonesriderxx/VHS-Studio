# VHS Studio: provider-independent local automation

This interface works with any agent capable of running a local program or
connecting to a standard MCP stdio server. It has no dependency on an AI vendor,
model, subscription or API key. A web chat without local tools cannot access
local files or start this application merely because it is running.

## Discover and inspect

`"C:\path\VHS Studio.exe" --describe` returns JSON containing the agent guide,
option schema, defaults and CPU topology. With a windowed executable, invoke
using inherited stdout pipes (e.g. Python subprocess capture_output); a console
window is not opened. GUI instances advertise local descriptors under
`%LOCALAPPDATA%\VHS Studio\instances\*.json`. Validate the PID and process
creation time; a crash can leave a stale descriptor. Descriptors are hints for
agents, not automatic registration into ChatGPT, Claude or another client.

## Direct JSON calls without MCP configuration

Run `"C:\path\VHS Studio.exe" --api request.json response.json`.
Request and response paths must differ. Wait for the command to exit and read
the UTF-8 response. Nonzero exit and `ok:false` indicate failure.

```json
{"tool":"scan_folder","arguments":{"source":"C:\\VHS","output":"C:\\Restored","options":{"deinterlace":true,"method":"QTGMC","upscale":false,"ocr":true,"ocr_rate":1,"cpu_mode":"background","limit":2}}}
```

All operations and arguments are described by `--describe`. Begin with
`{"tool":"get_options","arguments":{}}`. Then scan, poll `get_job_status`,
review the plan, and invoke `start_processing` only for authorized work.
Use its NEW job id for status, log, cancellation and OCR calls. Processing
continues after the initiating API command exits. No work is cancelled when
an MCP client disconnects. Inspect completion events and per-video results;
an idle process or a finished scan does not mean a render succeeded.

## Standard MCP

Launch the same executable with `--mcp`. It uses newline-delimited JSON-RPC over
stdin/stdout via the official Python MCP SDK. No HTTP endpoint or open network
port is involved. Configure the executable as the command and `["--mcp"]` as
arguments in your client's local stdio-server configuration. JSON formats and
configuration locations depend on the client; a GUI's example is not a universal
configuration file. Clients that support only remote HTTP MCP cannot directly
launch this local stdio server.

Tools: `get_options`, `scan_folder`, `start_processing`, `get_job_status`,
`read_job_logs`, `cancel_job`, `list_jobs`, `read_ocr`, `submit_ocr_review`. Tool descriptions and the
options JSON Schema are provided at runtime. Jobs persist under
`%LOCALAPPDATA%\VHS Studio\jobs`. GUI jobs currently remain separate: they are
not attachable or cancellable through these tools. Output/archive locks prevent
overlapping publication to the same destination.

## Resource modes and data safety

CPU modes adapt to the detected machine. Gentle uses at most four physical
cores and Idle priority; balanced leaves one physical core where possible;
full uses available cores; background uses up to two cores (roughly a quarter
of detected cores), Idle priority, and pauses of three times the measured
inference call between GPU frames. This pacing is not a 25% GPU utilization
limit: calls may queue GPU work, peaks and VRAM usage remain, and gaming frame
times are not guaranteed. For GPU-heavy games, leave upscaling disabled.

Export preserves inputs. Archive mode moves verified previous versions into
archive folders. OCR never justifies automatic date correction or splitting:
use `read_ocr` and visually review original frames. The app has no cloud upload.

## Deutsch

Die Schnittstelle ist unabhängig von ChatGPT, Claude oder anderen Anbietern.
Eine KI braucht entweder lokalen Programmzugriff oder einen kompatiblen
MCP-Client. `--describe` erklärt Optionen und Ablauf direkt maschinenlesbar.
`--api Anfrage.json Antwort.json` benötigt keinen MCP-Konfigurationseintrag.
Eine laufende GUI wird als lokaler Hinweis vermerkt, aber nicht automatisch
bei KI-Clients angemeldet. GUI-Läufe und API-/MCP-Läufe sind aktuell getrennt.
Der Hintergrundmodus reduziert Konkurrenz, garantiert aber keine ruckelfreien
Spiele. Bei GPU-intensiven Spielen die KI-Vergrößerung ausgeschaltet lassen.

## Saved settings and optional login startup

The GUI saves its last configuration to `%LOCALAPPDATA%\VHS Studio\settings.json`.
The separate opt-in startup profile is `autostart.json` in the same folder.
Changing GUI settings does not change an enabled startup profile until Apply
profile is clicked. The UI creates only a shortcut in the CURRENT USER's Startup
folder; no elevation, machine-wide task or Windows service is used. The shortcut
launches `--autostart` after user sign-in, not before sign-in or at power-on.
Never install or activate this profile merely to test an integration.

The headless runner scans and processes one saved batch per login, stores API
jobs normally, and writes `autostart-status.json`. Its completion ledger skips
successful startup jobs when source/configuration and output file identities
still match. Failed jobs are eligible on the next login. Keep the executable at
its configured location. If network paths are unavailable, the error is logged;
there is no endless retry loop. Disabling startup prevents future launches,
but does not cancel an already running processing job. GUI preferences and the
startup profile remain on the current user's machine when the EXE is copied.

OCR SQLite/JSON/CSV and processing logs remain inside the chosen destination:
`_Administration\VHS-Studio` (or existing German `_Verwaltung\VHS-Studio`). Preferences do not move those results to an AI service.

## Visual review write-back

SQLite is authoritative. Raw `ocr_stamps` remain unchanged. Each visual review
is appended to `ocr_reviews`; `ocr_latest_reviews` exposes the latest review per
finding. `OCR-Fundstellen.json` version 2 contains video IDs, each hit's latest
`review`, and per-video `review_history`. CSV includes raw and reviewed columns.
Older databases migrate additively; OCR observations are not replaced.

Use `submit_ocr_review` via MCP or `--api` to save reviews. Its runtime tool schema
defines every field. Exact finding key: video_id, second, camera_date. Supply
expected_review_id (0 for unreviewed) to reject concurrent stale writes. Decisions
are verified/corrected/uncertain/rejected. Confirmed/corrected entries require an
ISO date; uncertain/rejected entries cannot claim one. A boundary requires a
nonnegative uncertainty in seconds and refers to the actual reviewed video
timeline. Video size/mtime must still match the OCR record. Evidence must name
the frames and rationale. Provider/model are self-reported; unknown model is
null. These records are review proposals, never automatic cutting instructions.

Successful submission regenerates JSON and CSV. Each file is atomically replaced;
the pair is not a single atomic unit. If CSV is open/locked, the response says
saved=true, exports_updated=false: SQLite remains authoritative and the review
is visible in the GUI. Copying a fresh review prompt regenerates exports again.
The open Date findings tab reads SQLite every two seconds even without a running
OCR worker, preserves selection and shows reviewed date, status, boundary and
attribution. Double-click or Enter opens evidence and revision history. A plain
chat without local tools cannot write files: it must return the request data and
clearly state that nothing was saved. The GUI currently has no request importer.
