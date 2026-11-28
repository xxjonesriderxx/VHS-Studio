# Third-party components

## Download-based release

The published launcher contains the project's own executable and readable app
sources, metadata and download recipes. It does not embed Python, third-party
Python modules, video binaries, model weights or copied C/C++ runtime DLLs.
It uses the .NET Framework supplied by Windows.

On first use, the end user's computer obtains a pinned CPython runtime directly
from [Astral Python Build Standalone](https://github.com/astral-sh/python-build-standalone),
and original Python wheels directly from PyPI. Missing video components and the
optional model come from the upstream addresses below. The launcher checks
archive hashes and installs within the current user's folder, without elevation.
Upstream license files remain with those locally obtained packages. The complete
Python wheel list and hashes are in `bootstrap-lock.json`.

Distributing a populated cache or prefilled offline package requires compliance
with the licenses of everything in that package. The project's MIT license
applies to its own code.

The application license applies to original project code. Independent tools,
libraries and model weights retain their terms. No endorsement is implied.

| Component | Source / provenance | Terms |
| --- | --- | --- |
| Python 3.12 | https://www.python.org/ | Python Software Foundation license |
| FFmpeg / ffprobe | https://ffmpeg.org/download.html ; versioned Windows release from https://github.com/GyanD/codexffmpeg/releases | GPL build; preserve the included notices and corresponding-source obligations |
| VapourSynth | https://github.com/vapoursynth/vapoursynth ; pinned PyPI wheel | LGPL and included component notices |
| VapourSynth plugins | Exact version, wheel URL and provenance recorded in runtime-manifest.json | Per-plugin GPL/LGPL/MIT or other upstream terms; original notices retained |
| vs-jetpack / jetpytools | https://github.com/Jaded-Encoding-Thaumaturgy/vs-jetpack | MIT |
| NumPy / SciPy | https://numpy.org/ ; https://scipy.org/ | BSD and included numerical-library notices |
| CustomTkinter | https://github.com/TomSchimansky/CustomTkinter | Upstream license included |
| Pillow | https://github.com/python-pillow/Pillow | MIT-CMU and included library notices |
| Python MCP SDK | https://github.com/modelcontextprotocol/python-sdk | MIT |
| PyWin32 / PyWinRT | https://github.com/mhammond/pywin32 ; https://github.com/pywinrt/pywinrt | Included upstream notices |
| upscale-ncnn-py 1.2.0 | https://github.com/TNTwise/Universal-NCNN-upscaler-python/releases/tag/2024-08-21 | Original wheel includes GPLv3; BSD metadata conflicts. Downloaded directly, not embedded in the launcher; do not assume a BSD redistribution grant. |
| dfttest2 Python package and CPU plugin | https://pypi.org/project/dfttest2/11.1.1/ | Actual included license is GPLv3; CPU package metadata differs. Corresponding source and compatibility review required. |
| BestSource native plugin | https://github.com/vapoursynth/bestsource/tree/R23 | MIT wrapper includes a separate static GPLv3-or-later FFmpeg build and dependencies; wrapper license does not cover the whole DLL. |
| OpenProteus Compact | SiroSky; https://github.com/Sirosky/Upscale-Hub/releases/tag/OpenProteus | CC BY-NC 4.0; noncommercial restriction |
| OpenProteus NCNN conversion | https://github.com/TNTwise/real-video-enhancer-models/releases/tag/models | Same model rights remain applicable; format conversion does not relicense the weights |

The original model license is at
https://github.com/Sirosky/Upscale-Hub/blob/main/LICENSE.md. The optional weights
are obtained separately; the interface identifies their noncommercial terms.
Model weights are not part of the Git repository.

The upstream package and per-file checksums are pinned in runtime-manifest.json
and bootstrap-lock.json. Dependencies are obtained from those upstreams;
this repository contains no copied upstream source trees or private build paths.
