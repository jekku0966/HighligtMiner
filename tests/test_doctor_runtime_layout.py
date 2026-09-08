from pathlib import Path
from types import SimpleNamespace

from highlightminer import doctor, runtime


def test_doctor_loads_core_dlls_from_frozen_nested_layout(monkeypatch, tmp_path, capsys):
    cuda = tmp_path / 'runtime/cuda'
    cuda.mkdir(parents=True)
    for name in runtime.portable_cuda_core_dlls():
        (cuda / name).write_bytes(b'fixture')
    monkeypatch.setattr(runtime.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(runtime.sys, 'executable', str(tmp_path / 'HighlightMiner.exe'))
    windows = SimpleNamespace(name='nt', environ={}, pathsep=';', add_dll_directory=lambda _: object())
    monkeypatch.setattr(runtime, 'os', windows)
    monkeypatch.setattr(runtime, '_DLL_DIRECTORY_HANDLES', [])
    monkeypatch.setattr(doctor, 'os', windows)
    monkeypatch.setattr(doctor, '_webview2_runtime_version', lambda: 'test-version')
    monkeypatch.setattr(doctor, 'find_executable', lambda name: str(tmp_path / 'bin' / f'{name}.exe'))
    monkeypatch.setattr(doctor.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='h264_nvenc'))
    loaded = []
    monkeypatch.setattr(doctor.ctypes, 'WinDLL', lambda name: loaded.append(Path(name)), raising=False)
    monkeypatch.setitem(doctor.sys.modules, 'webview', SimpleNamespace())
    monkeypatch.setitem(doctor.sys.modules, 'ctranslate2', SimpleNamespace(
        __version__='test', get_cuda_device_count=lambda: 1,
        get_supported_compute_types=lambda _: {'float16'}))
    monkeypatch.setitem(doctor.sys.modules, 'faster_whisper', SimpleNamespace(__version__='test'))
    assert doctor.run_doctor() == 0
    assert loaded == [cuda / name for name in runtime.portable_cuda_core_dlls()]
    assert f'Portable CUDA DLL root: {cuda}' in capsys.readouterr().out
