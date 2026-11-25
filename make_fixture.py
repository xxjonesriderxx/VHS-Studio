"""Generate a two-second synthetic fixture; never uses personal recordings."""
from pathlib import Path
import subprocess
import runtime_components

def main():
    root=Path(__file__).resolve().parent
    runtime_components.ensure('media')
    ffmpeg=runtime_components.asset('media','bin/ffmpeg.exe')
    subprocess.run([str(ffmpeg),'-y','-v','error','-f','lavfi','-i',
        'testsrc2=size=320x240:rate=50:duration=2','-f','lavfi','-i',
        'sine=frequency=440:sample_rate=48000:duration=2','-vf','tinterlace=mode=interleave_top',
        '-c:v','mpeg2video','-flags','+ildct+ilme','-c:a','ac3','-shortest',
        str(root/'test-source.mkv')],check=True)
    folder=root/'test-input';folder.mkdir(exist_ok=True)
    import shutil
    shutil.copyfile(root/'test-source.mkv',folder/'2001-01-01 - Original.mkv')

if __name__=='__main__':
    main()
