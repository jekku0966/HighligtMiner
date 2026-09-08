import struct
from pathlib import Path

import pytest

from tools.release_layout import CUDA_FILES, DOCUMENTS, FFMPEG_FILES, validate_layout


def package_fixture(root):
    names = ["HighlightMiner.exe", "settings.json", "highlightminer.db", ".streamlit/config.toml",
             "_internal/highlightminer/app.py", "_internal/highlightminer/preview_component/index.html",
             *DOCUMENTS, *(f"bin/{n}" for n in FFMPEG_FILES), *(f"runtime/cuda/{n}" for n in CUDA_FILES)]
    for name in names:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"fixture")
    return root


def test_complete_nested_release_passes(tmp_path):
    validate_layout(package_fixture(tmp_path), require_runtimes=True)


@pytest.mark.parametrize("name", [*(f"bin/{n}" for n in FFMPEG_FILES),
                                  *(f"runtime/cuda/{n}" for n in CUDA_FILES)])
def test_root_runtime_cannot_substitute_for_nested_file(tmp_path, name):
    root = package_fixture(tmp_path)
    (root / name).rename(root / Path(name).name)
    with pytest.raises(ValueError, match="Missing or empty packaged file"):
        validate_layout(root, require_runtimes=True)


def test_ci_can_omit_external_runtimes_but_official_release_cannot(tmp_path):
    root = package_fixture(tmp_path)
    for name in FFMPEG_FILES:
        (root / 'bin' / name).unlink()
    for name in CUDA_FILES:
        (root / 'runtime/cuda' / name).unlink()
    validate_layout(root)
    with pytest.raises(ValueError):
        validate_layout(root, require_runtimes=True)


@pytest.mark.parametrize("name", ["README.md", "V0.2_DEV.md", "BUILD_WINDOWS.md", "CUDA_SETUP.md",
                                  "SETTINGS.md", "SECURITY.md", "RERUNS_AND_LEARNING.md",
                                  "CHANGELOG.md", "runtime/cuda/unapproved.dll"])
def test_release_rejects_development_docs_and_unapproved_runtimes(tmp_path, name):
    root = package_fixture(tmp_path)
    (root / name).write_bytes(b"not for release")
    with pytest.raises(ValueError, match="Unexpected"):
        validate_layout(root, require_runtimes=True)


def test_required_files_must_not_be_empty(tmp_path):
    root = package_fixture(tmp_path)
    (root / 'bin/ffmpeg.exe').write_bytes(b'')
    with pytest.raises(ValueError, match="bin/ffmpeg.exe"):
        validate_layout(root, require_runtimes=True)


def test_icon_contains_windows_sizes():
    data = (Path(__file__).resolve().parents[1] / 'assets/highlightminer.ico').read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', data)
    assert (reserved, kind) == (0, 1)
    sizes = set()
    for i in range(count):
        width, height, _, _, _, _, length, offset = struct.unpack_from('<BBBBHHII', data, 6 + i * 16)
        sizes.add((width or 256, height or 256))
        assert length > 0 and offset + length <= len(data)
    assert sizes == {(s, s) for s in (16, 24, 32, 48, 64, 128, 256)}
