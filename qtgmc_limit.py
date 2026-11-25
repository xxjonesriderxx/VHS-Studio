"""Render a constant-rate interlaced source through QTGMC and FFmpeg."""

import subprocess
import sys

def limit_cpu(physical_cores=4, idle=True):
    import ctypes
    from ctypes import wintypes
    import psutil

    class ProcessorInfo(ctypes.Structure):
        _fields_ = [
            ("mask", ctypes.c_size_t),
            ("relationship", ctypes.c_int),
            ("details", ctypes.c_uint64 * 2),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    topology = kernel.GetLogicalProcessorInformation
    topology.argtypes = [ctypes.POINTER(ProcessorInfo), ctypes.POINTER(wintypes.DWORD)]
    topology.restype = wintypes.BOOL
    size = wintypes.DWORD()
    if topology(None, ctypes.byref(size)) or ctypes.get_last_error() != 122:
        raise ctypes.WinError(ctypes.get_last_error())
    entries = (ProcessorInfo * (size.value // ctypes.sizeof(ProcessorInfo)))()
    if not topology(entries, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())

    process = psutil.Process()
    allowed = set(process.cpu_affinity())
    cores = [
        sorted(cpu for cpu in allowed if entry.mask & (1 << cpu))
        for entry in entries if entry.relationship == 0
    ]
    cores = sorted(core for core in cores if core)
    selected_cores = cores[-physical_cores:] if physical_cores else cores
    selected = [cpu for core in selected_cores for cpu in core]
    if not selected:
        raise RuntimeError("No eligible processors found")
    process.cpu_affinity(selected)
    process.nice(psutil.IDLE_PRIORITY_CLASS if idle else psutil.BELOW_NORMAL_PRIORITY_CLASS)
    return len(selected)


def render(ffmpeg, source, destination, *encoder_args, cpu_count):
    import vapoursynth as vs
    from vsdeinterlace import QTempGaussMC

    core = vs.core
    core.num_threads = cpu_count
    original = core.bs.VideoSource(source=source, cachemode=0)
    if original.fps <= 0 or original.format is None:
        raise ValueError("QTGMC requires a constant video format and frame rate")

    props = original.get_frame(0).props
    field_order = props.get("_FieldBased", 0)
    if field_order not in (1, 2):
        # Match BWDIF's top-field-first fallback when the source lacks field order.
        field_order = 1 if props.get("TopFieldFirst", 1) == 0 and props.get("_FieldBased") is None else 2
    original = original.std.SetFrameProps(_FieldBased=field_order)
    clip = QTempGaussMC().deinterlace(original)

    sar_num, sar_den = props.get("_SARNum", 1), props.get("_SARDen", 1)
    color_args = []
    for prop, option in (
        ("_Matrix", "-colorspace"),
        ("_Primaries", "-color_primaries"),
        ("_Transfer", "-color_trc"),
    ):
        if prop in props:
            color_args.extend((option, str(int(props[prop]))))
    if "_Range" in props:
        color_args.extend(("-color_range", "tv" if props["_Range"] == vs.RANGE_LIMITED else "pc"))

    args = [
        ffmpeg, "-n", "-nostdin", "-v", "warning",
        "-f", "yuv4mpegpipe", "-i", "pipe:0", "-i", source,
        "-map", "0:v:0", "-map", "1:a?",
        "-vf", f"setsar={sar_num}/{sar_den}", *color_args,
        *encoder_args, destination,
    ]
    with subprocess.Popen(args, stdin=subprocess.PIPE, creationflags=subprocess.IDLE_PRIORITY_CLASS) as encoder:
        try:
            clip.output(encoder.stdin, y4m=True)
            encoder.stdin.close()
        except BaseException:
            encoder.kill()
            raise
        if encoder.wait():
            raise subprocess.CalledProcessError(encoder.returncode, args)


if __name__ == "__main__":
    arguments = sys.argv[1:]
    cpu_count = limit_cpu()
    if arguments[0] == "--exec":
        sys.exit(subprocess.call(arguments[1:], creationflags=subprocess.IDLE_PRIORITY_CLASS))
    if arguments[0] == "--low-priority":
        arguments = arguments[1:]
    render(*arguments, cpu_count=cpu_count)
