# VHS Studio

**Restore digitised VHS family recordings with a simple Windows interface.**

Correct interlacing, enhance details and find on-screen dates to make old family
recordings easier to watch and organise. The app speaks **English and German**.

> I'm a software engineer, but my free time is limited. I'm building VHS Studio
> with AI coding agents — essentially vibe-coding — to turn a personal restoration
> workflow into a tool others can use.
>
> This is an early release. Test on copies of your footage and inspect the results.
> Contributions, careful reviews and reproducible bug reports are welcome.

## Download

Get the latest files from [Releases](https://github.com/xxjonesriderxx/VHS-Studio/releases/latest):

| Download | Choose this when… |
| --- | --- |
| **Portable ZIP** | You want the launcher with its documentation. Extract the folder and run the EXE. Internet is needed on first use. |
| **Standalone EXE** | You prefer one file. Python and required components download directly from their original providers on first use. |

This release distributes the project's own launcher and app sources. It obtains
a pinned Python runtime from Astral's Python Build Standalone project, original
Python wheels from PyPI, and video components from their upstream providers.
Downloads are checked against pinned SHA-256 hashes and stay in your user folder.
No administrator rights or system-wide installation are required. Components
already downloaded can be reused offline. A prefilled, fully offline bundle is
not included in this release. The app checks for updates at startup and waits for
running tasks before applying them.

## What you can do

- **Correct interlacing:** QTGMC for quality, or BWDIF for faster processing.
- **Enhance details:** local OpenProteus 2× upscaling on a suitable Vulkan GPU.
- **Read date stamps:** adjustable OCR sampling to find different recording days
  inside one digitised tape.
- **Review with AI:** copy a local review prompt; an agent can inspect frames and
  write back dates, boundaries, uncertainty and its provider/model attribution.
- **Run in the background:** resource modes, optional login startup and Windows
  notifications for start, completion and errors.
- **Automate locally:** standard MCP or a JSON command interface; see
  [AI-CONTROL.md](AI-CONTROL.md).

**OCR is a clue, not a verified date.** Camera clocks can be wrong too. Raw
readings are preserved separately from AI reviews. The app does not automatically
cut videos or send footage to an AI provider.

## Getting started

1. Choose your recordings and an output folder.
2. Enable the restoration steps you want.
3. Check the files and inspect the queue.
4. Start restoration and review the resulting video.

Export preserves source files. Optional family-archive mode moves previous
versions into archive folders after verification. New archives use English folder
names; existing German archive folders are recognised and reused. Missing
structures can be created directly from the interface.

Settings are remembered locally. Login startup is off until you enable it and
uses a separate saved profile. Windows may suppress notifications under Do Not
Disturb. Background/Gaming mode reduces resource contention but cannot guarantee
uninterrupted gaming.

OCR data, reviews and logs live under the destination's
`_Administration/VHS-Studio` folder, or its existing German `_Verwaltung`
equivalent. SQLite is the source of truth; JSON and CSV exports are included.
The Date findings table refreshes automatically. Double-click a row for evidence
and review history.

## Requirements

Windows 10/11 x64 is the current target. QTGMC requires supported CPU features;
OpenProteus needs a compatible Vulkan graphics driver. Date OCR uses Windows OCR
and an available recognition language. Other systems are not yet validated.

## Development

Build the launcher on Windows with Python 3.12+ and the Windows .NET Framework
C# compiler. The build embeds only the project's own source files and metadata:

```powershell
python build_bootstrap.py
```

The build creates the launcher in `bootstrap-dist/`. Dependency versions,
original download sources and checksums are pinned in the manifests. Binaries,
weights, local settings, databases, logs and family footage are excluded from Git.
Please keep personal files and paths out of public issue reports.

## License and credits

Original app code: **MIT** — see [LICENSE](LICENSE). Third-party tools, libraries
and model weights retain their own licenses; their redistribution and source-code
requirements still apply. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

**OpenProteus by SiroSky uses CC BY-NC 4.0, including a noncommercial restriction.**
It does not share the application's MIT license. The NCNN conversion comes from
REAL Video Enhancer's model releases; no endorsement is implied.

Thanks to [FFmpeg](https://ffmpeg.org/),
[VapourSynth](https://github.com/vapoursynth/vapoursynth),
[vs-jetpack](https://github.com/Jaded-Encoding-Thaumaturgy/vs-jetpack),
[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter),
[OpenProteus](https://github.com/Sirosky/Upscale-Hub/releases/tag/OpenProteus) and
[upscale-ncnn-py](https://pypi.org/project/upscale-ncnn-py/).

Provided without warranty. Restoration cannot recover detail that was never
captured, and AI enhancement can introduce errors.
