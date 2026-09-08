from pathlib import Path

from highlightminer import runtime


def test_app_root_source_points_to_repository() -> None:
    expected = Path(runtime.__file__).resolve().parent.parent
    assert runtime.app_root() == expected


def test_app_root_uses_executable_when_frozen(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "HighlightMiner.exe"
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "executable", str(exe))

    assert runtime.app_root() == tmp_path


def test_bundle_root_uses_meipass_when_frozen(monkeypatch, tmp_path: Path) -> None:
    bundle = tmp_path / "_internal"
    monkeypatch.setattr(runtime.sys, "frozen", True, raising=False)
    monkeypatch.setattr(runtime.sys, "_MEIPASS", str(bundle), raising=False)

    assert runtime.bundle_root() == bundle
    assert runtime.bundled_path("highlightminer", "app.py") == bundle / "highlightminer" / "app.py"


def test_source_cuda_runtime_prefers_dedicated_directory(monkeypatch, tmp_path: Path) -> None:
    cuda_root = tmp_path / "runtime" / "cuda"
    cuda_root.mkdir(parents=True)
    for name in runtime.portable_cuda_core_dlls():
        (cuda_root / name).touch()

    monkeypatch.setattr(runtime, "app_root", lambda: tmp_path)
    monkeypatch.setattr(runtime, "is_frozen", lambda: False)

    assert runtime.portable_cuda_root() == cuda_root


def test_source_cuda_runtime_falls_back_to_app_root_when_incomplete(monkeypatch, tmp_path: Path) -> None:
    cuda_root = tmp_path / "runtime" / "cuda"
    cuda_root.mkdir(parents=True)
    (cuda_root / runtime.portable_cuda_core_dlls()[0]).touch()

    monkeypatch.setattr(runtime, "app_root", lambda: tmp_path)
    monkeypatch.setattr(runtime, "is_frozen", lambda: False)

    assert runtime.portable_cuda_root() == tmp_path


def test_frozen_cuda_prefers_complete_nested_runtime(monkeypatch, tmp_path):
    from types import SimpleNamespace
    nested = tmp_path / 'runtime/cuda'
    nested.mkdir(parents=True)
    for name in runtime.portable_cuda_core_dlls():
        (nested / name).write_bytes(b'nested')
        (tmp_path / name).write_bytes(b'legacy')
    monkeypatch.setattr(runtime.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(runtime.sys, 'executable', str(tmp_path / 'HighlightMiner.exe'))
    registered = []
    handles = []
    monkeypatch.setattr(runtime, '_DLL_DIRECTORY_HANDLES', handles)
    fake_os = SimpleNamespace(name='nt', pathsep=';', environ={'PATH': 'C:\\Windows'},
                              add_dll_directory=lambda p: registered.append(p) or 'handle')
    monkeypatch.setattr(runtime, 'os', fake_os)
    assert runtime.configure_windows_cuda_dll_search() == nested
    assert registered == [str(nested)]
    assert handles == ['handle']
    assert fake_os.environ['PATH'].split(';')[0] == str(nested)
    runtime.configure_windows_cuda_dll_search()
    assert fake_os.environ['PATH'].count(str(nested)) == 1


def test_frozen_cuda_incomplete_nested_runtime_uses_legacy_root(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(runtime.sys, 'executable', str(tmp_path / 'HighlightMiner.exe'))
    nested = tmp_path / 'runtime/cuda'
    nested.mkdir(parents=True)
    (nested / runtime.portable_cuda_core_dlls()[0]).touch()
    for name in runtime.portable_cuda_core_dlls():
        (tmp_path / name).touch()
    assert runtime.portable_cuda_root() == tmp_path


def test_frozen_ffmpeg_prefers_bin_over_legacy_root_and_path(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from highlightminer import media
    monkeypatch.setattr(runtime.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(runtime.sys, 'executable', str(tmp_path / 'HighlightMiner.exe'))
    monkeypatch.setattr(media, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(media.shutil, 'which', lambda _: 'system-tool')
    (tmp_path / 'bin').mkdir()
    for name in ('ffmpeg', 'ffprobe'):
        (tmp_path / f'{name}.exe').touch()
        nested = tmp_path / 'bin' / f'{name}.exe'
        nested.touch()
        assert media.find_executable(name) == str(nested)
