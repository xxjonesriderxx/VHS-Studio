# Third-party components

The application license applies to original project code, not to independent
tools, libraries or model weights. License texts are included in the application
and in the verified component folders. No endorsement by upstream projects is
implied. Consult the exact upstream notices when redistributing these binaries.

| Component | Source / provenance | Terms |
| --- | --- | --- |
| Python 3.12 | https://www.python.org/ | Python Software Foundation license |
| FFmpeg / ffprobe | https://ffmpeg.org/download.html ; versioned Windows release from https://github.com/GyanD/codexffmpeg/releases | GPL build; preserve the included notices and corresponding-source obligations |
| VapourSynth | https://github.com/vapoursynth/vapoursynth ; pinned PyPI wheel | LGPL and included component notices |
| VapourSynth plugins | Exact version, wheel URL and provenance recorded in runtime-manifest.json | Per-plugin GPL/LGPL/MIT or other upstream terms; original notices retained |
| vs-jetpack / jetpytools | https://github.com/Jaded-Encoding-Thaumaturgy/vs-jetpack | MIT |
| NumPy / SciPy | https://numpy.org/ ; https://scipy.org/ | BSD and included numerical-library notices |
| CustomTkinter | https://github.com/TomSchimansky/CustomTkinter | Upstream license included |
| Pillow | https://python-pillow.github.io/ | HPND and included library notices |
| Python MCP SDK | https://github.com/modelcontextprotocol/python-sdk | MIT |
| PyWin32 / PyWinRT | https://github.com/mhammond/pywin32 ; https://github.com/pywinrt/pywinrt | Included upstream notices |
| upscale-ncnn-py | https://pypi.org/project/upscale-ncnn-py/1.2.0/ | BSD-3-Clause plus included native-library notices |
| OpenProteus Compact | SiroSky; https://github.com/Sirosky/Upscale-Hub/releases/tag/OpenProteus | CC BY-NC 4.0; noncommercial restriction |
| OpenProteus NCNN conversion | https://github.com/TNTwise/real-video-enhancer-models/releases/tag/models | Same model rights remain applicable; format conversion does not relicense the weights |

The original model license is at
https://github.com/Sirosky/Upscale-Hub/blob/main/LICENSE.md. Its full text and
attribution are included. Model weights are not part of the Git repository.

The upstream package and per-file checksums are pinned in runtime-manifest.json
and embedded-manifest.json. Dependencies are obtained from those upstreams;
this repository contains no copied upstream source trees or private build paths.
