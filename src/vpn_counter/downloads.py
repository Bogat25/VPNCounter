from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

MODEL_REPOSITORIES = {
    "large-v3": "Systran/faster-whisper-large-v3",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "small": "Systran/faster-whisper-small",
}
MODEL_FILES = {
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.json",
    "vocabulary.txt",
}


class ByteProgress:
    """Aggregate file bytes, including resumed/cached data, into one percentage."""

    def __init__(self, total: int, notify: Callable[[int], None]) -> None:
        if total <= 0:
            raise ValueError("The download has no advertised file size.")
        self.total = total
        self.completed = 0
        self._notify = notify
        self._last_percent = -1
        self._lock = threading.Lock()
        self.report(0)

    def report(self, file_bytes: int | float) -> None:
        with self._lock:
            # Only a successful return from all downloads can report 100%.
            percent = max(0, min(99, int(100 * (self.completed + file_bytes) / self.total)))
            if percent != self._last_percent:
                self._last_percent = percent
                self._notify(percent)

    def file_completed(self, size: int) -> None:
        self.completed += size
        self.report(0)

    def finish(self) -> None:
        self._notify(100)

    def tqdm_class(self):
        from tqdm.auto import tqdm

        progress = self

        class CallbackProgress(tqdm):
            def __init__(self, *args, **kwargs):
                kwargs["disable"] = True  # A windowed EXE has no console stream.
                super().__init__(*args, **kwargs)
                progress.report(self.n)

            def update(self, n=1):
                # Disabled tqdm skips its byte counter, so maintain it explicitly.
                self.n += n or 0
                progress.report(self.n)

            def reset(self, total=None):
                self.n = 0
                if total is not None:
                    self.total = total
                progress.report(0)

            def update_transfer(self, n):
                # Xet distinguishes compressed network bytes from reconstructed
                # file bytes. Count only the latter against the advertised size.
                pass

            def set_transfer_postfix_str(self, text, refresh=False):
                pass

        return CallbackProgress


def download_model(name: str, directory: Path, notify: Callable[[int], None]) -> str:
    from huggingface_hub import HfApi, hf_hub_download

    repository = MODEL_REPOSITORIES[name]
    info = HfApi(token=False).model_info(repository, files_metadata=True, timeout=20)
    files = [file for file in info.siblings or () if file.rfilename in MODEL_FILES]
    if not info.sha or not files or any(file.size is None for file in files):
        raise RuntimeError("The model server did not provide download sizes. Please try again.")
    progress = ByteProgress(sum(file.size for file in files), notify)
    # Small files first, then weights. Pin every file to the same model revision.
    for file in sorted(files, key=lambda item: (item.rfilename == "model.bin", item.rfilename)):
        hf_hub_download(
            repository,
            file.rfilename,
            revision=info.sha,
            local_dir=str(directory),
            token=False,
            tqdm_class=progress.tqdm_class(),
        )
        progress.file_completed(file.size)
    progress.finish()
    return str(directory)
