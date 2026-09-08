"""Validate portable output without importing the installed application."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CUDA_FILES = (
    "cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll",
    "cudnn_adv64_9.dll", "cudnn_cnn64_9.dll",
    "cudnn_engines_precompiled64_9.dll", "cudnn_engines_runtime_compiled64_9.dll",
    "cudnn_graph64_9.dll", "cudnn_heuristic64_9.dll", "cudnn_ops64_9.dll",
)
OPTIONAL_CUDA_FILES = ("zlibwapi.dll",)
FFMPEG_FILES = ("ffmpeg.exe", "ffprobe.exe")
DOCUMENTS = ("README.txt", "LICENSE", "ATTRIBUTIONS.md")


def validate_layout(root: Path, *, require_runtimes: bool = False) -> None:
    """CI may omit external runtimes; official releases must include all of them."""
    required = ["HighlightMiner.exe", "settings.json", "highlightminer.db",
                ".streamlit/config.toml", "_internal/highlightminer/app.py",
                "_internal/highlightminer/preview_component/index.html", *DOCUMENTS]
    if require_runtimes:
        required += [f"bin/{name}" for name in FFMPEG_FILES]
        required += [f"runtime/cuda/{name}" for name in CUDA_FILES]
    errors = []
    for name in required:
        path = root / name
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"Missing or empty packaged file: {name}")
    for name in ("bin", "runtime/cuda", "_internal", ".streamlit"):
        if not (root / name).is_dir():
            errors.append(f"Missing packaged directory: {name}")
    allowed = {"HighlightMiner.exe", "settings.json", "highlightminer.db",
               "bin", "runtime", "_internal", ".streamlit", *DOCUMENTS}
    for entry in root.iterdir():
        if entry.name not in allowed:
            errors.append(f"Unexpected release-root entry: {entry.name}")
    for directory, names in (("bin", FFMPEG_FILES), ("runtime", ("cuda",)),
                             ("runtime/cuda", CUDA_FILES + OPTIONAL_CUDA_FILES)):
        path = root / directory
        if path.is_dir():
            for entry in path.iterdir():
                if entry.name not in names:
                    errors.append(f"Unexpected packaged runtime entry: {directory}/{entry.name}")
    if errors:
        raise ValueError("\n".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--require-runtimes", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("release_documents.json").read_text(encoding="utf-8"))
    if manifest != {"required": list(DOCUMENTS), "optional": []}:
        raise SystemExit("Release document manifest does not match the portable layout.")
    try:
        validate_layout(args.root, require_runtimes=args.require_runtimes)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print("Portable release layout verified.")


if __name__ == "__main__":
    main()
