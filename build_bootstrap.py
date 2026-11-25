"""Build the source-only Windows launcher using the system .NET Framework compiler."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

from app_version import VERSION

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = (
    "app.py", "app_updates.py", "app_version.py", "archive_layout.py", "automation.py",
    "bootstrap_setup.py", "engine.py", "i18n.py", "inference_backend.py", "mcp_server.py", "notifications.py",
    "preferences.py", "qtgmc_limit.py", "review.py", "review_store.py",
    "runtime_components.py", "ui_icons.py",
    "bootstrap-lock.json", "bootstrap-requirements.txt", "runtime-manifest.json",
    "LICENSE", "README.md", "AI-CONTROL.md", "THIRD-PARTY-NOTICES.md",
)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build(output):
    compiler = Path(os.environ["SystemRoot"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    lock_path = ROOT / "bootstrap-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8-sig"))
    if lock["version"] != VERSION or lock["requirements_sha256"] != sha256(ROOT / "bootstrap-requirements.txt"):
        raise ValueError("Release version or requirements digest does not match bootstrap-lock.json")
    year, month, day, *build_number = VERSION.split("-")
    file_version = ".".join(str(int(n)) for n in (year, month, day, *(build_number or ["0"])))
    with tempfile.TemporaryDirectory(prefix="vhs-launcher-") as temp:
        stage = Path(temp)
        payload = stage / "payload.zip"
        with zipfile.ZipFile(payload, "w") as archive:
            for name in SOURCE_FILES:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, (ROOT / name).read_bytes())
        metadata = stage / "BuildInfo.cs"
        metadata.write_text(
            'using System.Reflection;\n'
            '[assembly: AssemblyTitle("VHS Studio")]\n'
            '[assembly: AssemblyProduct("VHS Studio")]\n'
            f'[assembly: AssemblyFileVersion("{file_version}")]\n'
            f'[assembly: AssemblyVersion("{file_version}")]\n'
            'internal static class BuildInfo {\n'
            f'    internal const string PayloadHash = "{sha256(payload)}";\n'
            '}\n', encoding="utf-8",
        )
        built = stage / "VHS Studio.exe"
        shutil.copyfile(ROOT / "icon.py", stage / "icon.py")
        subprocess.run([sys.executable, "-I", str(stage / "icon.py")], check=True, cwd=stage)
        args = [str(compiler), "/nologo", "/target:winexe", "/platform:x64",
                "/optimize+", "/debug-", "/utf8output", "/out:" + str(built),
                "/win32icon:" + str(stage / "app.ico"),
                "/win32manifest:" + str(ROOT / "bootstrap/asInvoker.manifest"),
                "/resource:" + str(payload) + ",payload.zip",
                "/resource:" + str(lock_path) + ",bootstrap-lock.json"]
        for name in ("System", "System.Core", "System.Drawing", "System.Windows.Forms",
                     "System.Web.Extensions", "System.IO.Compression"):
            args.append("/reference:" + name + ".dll")
        args.extend((str(ROOT / "bootstrap/Launcher.cs"), str(metadata)))
        subprocess.run(args, check=True, cwd=ROOT)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".tmp", delete=False) as tmp:
            staged = Path(tmp.name)
        try:
            shutil.copyfile(built, staged)
            os.replace(staged, output)
        finally:
            staged.unlink(missing_ok=True)
    print(f"{output.name}  {output.stat().st_size} bytes  sha256={sha256(output)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "bootstrap-dist" / f"VHS-Studio-{VERSION}.exe")
    build(parser.parse_args().output.resolve())
