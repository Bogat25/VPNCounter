from types import SimpleNamespace

import pytest

from vpn_counter.downloads import ByteProgress, download_model


@pytest.fixture
def server(monkeypatch):
    import huggingface_hub

    files = [
        SimpleNamespace(rfilename=name, size=size)
        for name, size in (
            ("config.json", 20),
            ("tokenizer.json", 20),
            ("vocabulary.json", 20),
            ("model.bin", 40),
            ("README.md", 200),
        )
    ]
    requests = []

    class Api:
        def __init__(self, token):
            assert token is False

        def model_info(self, repository, files_metadata, timeout):
            assert files_metadata
            assert timeout == 20
            return SimpleNamespace(sha="public-model-revision", siblings=files)

    def fetch(repository, filename, *, revision, local_dir, token, tqdm_class):
        assert token is False
        assert revision == "public-model-revision"
        requests.append(filename)
        if filename == "model.bin":
            with tqdm_class(total=40, initial=10) as progress:
                progress.update(10)
                progress.update(20)
        # Small files model cached downloads: HF emits no byte callback.
        return str(local_dir)

    monkeypatch.setattr(huggingface_hub, "HfApi", Api)
    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fetch)
    return files, requests


def test_percentage_uses_bytes_includes_cached_and_resumed_data(server, tmp_path):
    _, requests = server
    percentages = []
    assert download_model("large-v3", tmp_path, percentages.append) == str(tmp_path)
    assert percentages == [0, 20, 40, 60, 70, 80, 99, 100]
    assert requests[-1] == "model.bin"
    assert "README.md" not in requests


def test_failed_download_never_reports_completion(server, tmp_path, monkeypatch):
    import huggingface_hub

    def fail(*args, **kwargs):
        with kwargs["tqdm_class"](total=20) as progress:
            progress.update(5)
        raise OSError("network unavailable")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", fail)
    percentages = []
    with pytest.raises(OSError, match="network unavailable"):
        download_model("small", tmp_path, percentages.append)
    assert percentages[0] == 0
    assert 100 not in percentages


def test_missing_file_size_cannot_produce_a_misleading_percentage(server, tmp_path):
    files, requests = server
    files[0].size = None
    percentages = []
    with pytest.raises(RuntimeError, match="download sizes"):
        download_model("turbo", tmp_path, percentages.append)
    assert not percentages
    assert not requests


def test_retry_resets_the_actual_byte_count_and_limits_ui_updates():
    percentages = []
    progress = ByteProgress(100, percentages.append)
    bar_class = progress.tqdm_class()
    with bar_class(total=100, initial=20) as bar:
        bar.update(20)
        bar.update(0)
        bar.reset()
        bar.update(100)
    progress.file_completed(100)
    progress.finish()
    assert percentages == [0, 20, 40, 0, 99, 100]


def test_xet_network_and_reconstruction_updates_cannot_double_count_bytes():
    from huggingface_hub.utils._xet_progress_reporting import XetDownloadProgressReporter

    percentages = []
    progress = ByteProgress(100, percentages.append)
    with XetDownloadProgressReporter(
        reconstruction_desc="model.bin",
        total=100,
        log_level=20,
        tqdm_class=progress.tqdm_class(),
    ) as reporter:
        for reconstructed, transferred in ((0, 50), (20, 70), (40, 100), (100, 120)):
            reporter.update_progress(
                SimpleNamespace(
                    total_bytes_completed=reconstructed,
                    total_transfer_bytes_completed=transferred,
                    total_bytes_completion_rate=0,
                    total_transfer_bytes_completion_rate=0,
                    total_bytes=100,
                )
            )
    progress.file_completed(100)
    progress.finish()
    assert percentages == [0, 20, 40, 99, 100]
