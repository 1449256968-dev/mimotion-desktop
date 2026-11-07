"""Package the tracked source and the built Windows EXE, never local settings."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")


def main():
    version = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))["version"]
    executable = ROOT / "dist" / "MiMotionDesktop.exe"
    if not executable.is_file():
        raise SystemExit("Build dist/MiMotionDesktop.exe first.")
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    exe_copy = release / executable.name
    exe_copy.write_bytes(executable.read_bytes())
    package = release / f"mimotion-desktop-{version}-win64.zip"
    docs = ("README.md", "README.en.md", "INSTALL.md", "LICENSE", "NOTICE.txt", "THIRD_PARTY_NOTICES.txt", "VERSION.json")
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(executable, executable.name)
        for name in docs:
            archive.write(ROOT / name, name)
    source = release / f"mimotion-desktop-{version}-source.zip"
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    files = [name for name in tracked if name]
    if not files:
        raise SystemExit("No tracked source files; add the intended public source to Git first.")
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT, check=True)
    subprocess.run(["git", "archive", "--format=zip", f"--output={source}", "HEAD"], cwd=ROOT, check=True)
    for artifact in (exe_copy, package, source):
        sha256_file(artifact)
        print(artifact.name)


if __name__ == "__main__":
    main()
