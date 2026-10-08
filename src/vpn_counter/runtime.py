from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

from vpn_counter.settings import data_directory

_DLL_HANDLES: list[object] = []
_DLL_DIRECTORIES: list[Path] | None = None


def configure_model_storage() -> None:
    """Keep downloader caches inside the model folder, in this process only."""
    cache = data_directory().absolute() / "models/.cache/huggingface"
    for name, directory in (
        ("HF_HOME", cache),
        ("HF_HUB_CACHE", cache / "hub"),
        ("HUGGINGFACE_HUB_CACHE", cache / "hub"),
        ("HF_XET_CACHE", cache / "xet"),
        ("HF_ASSETS_CACHE", cache / "assets"),
    ):
        os.environ[name] = str(directory)


@contextmanager
def audio_thread_context():
    """WASAPI needs COM initialized on the thread that opens its stream."""
    if sys.platform != "win32":
        yield
        return
    library = ctypes.WinDLL("ole32")
    initialize = library.CoInitializeEx
    initialize.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    initialize.restype = ctypes.c_long
    result = initialize(None, 0)  # COINIT_MULTITHREADED
    # An existing apartment is also usable; only successful initialization
    # increments the count that this context must balance on exit.
    if result < 0 and result != -2147417850:  # RPC_E_CHANGED_MODE
        raise OSError(f"Windows audio thread initialization failed ({result})")
    try:
        yield
    finally:
        if result >= 0:
            library.CoUninitialize()


def configure_gpu_libraries() -> list[Path]:
    """Expose NVIDIA wheel libraries to CTranslate2 in this process only."""
    global _DLL_DIRECTORIES
    if _DLL_DIRECTORIES is not None:
        return list(_DLL_DIRECTORIES)
    directories: list[Path] = []
    for root in sys.path:
        for package in ("cublas", "cudnn", "cuda_nvrtc"):
            for subfolder in ("bin", "lib"):
                directory = Path(root) / "nvidia" / package / subfolder
                if directory.is_dir() and directory not in directories:
                    directories.append(directory)
    if sys.platform == "win32":
        for directory in directories:
            _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
        if directories:
            os.environ["PATH"] = os.pathsep.join(str(path) for path in directories) + (
                os.pathsep + os.environ.get("PATH", "")
            )
        # CTranslate2 loads these libraries dynamically after model creation.
        for name in ("cublas64_12.dll", "cudnn64_9.dll"):
            for directory in directories:
                candidate = directory / name
                if candidate.is_file():
                    _DLL_HANDLES.append(ctypes.WinDLL(str(candidate)))
                    break
    _DLL_DIRECTORIES = directories
    return list(directories)


def gpu_description() -> str:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "NVIDIA GPU not detected"
