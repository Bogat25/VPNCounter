"""Count mentions in an existing rehearsal recording without opening a microphone."""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

from vpn_counter.engine import EngineOptions, load_model, transcribe_window
from vpn_counter.matching import MentionLedger, find_mentions
from vpn_counter.runtime import configure_gpu_libraries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", help="Path to a local WAV, MP3, or other supported audio file")
    parser.add_argument("--model", default="large-v3", choices=["large-v3", "turbo", "small"])
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument(
        "--expected", type=int, help="Known number of VPN mentions in the recording"
    )
    parser.add_argument("--confidence", type=float, default=0.45)
    parser.add_argument("--output", type=Path, help="Also save the JSON report locally")
    arguments = parser.parse_args()
    configure_gpu_libraries()
    from faster_whisper.audio import decode_audio

    audio = decode_audio(arguments.audio, sampling_rate=16000)
    model = load_model(EngineOptions(model=arguments.model, device=arguments.device), print)
    ledger = MentionLedger()
    mentions = []
    decode_seconds = []
    started = time.perf_counter()
    duration = len(audio) / 16000
    # Reproduce the live overlapping windows, including one final flush window.
    ends = list(range(3 * 16000, len(audio), 2 * 16000)) + [len(audio)]
    for end in ends:
        start = max(0, end - 6 * 16000)
        before = time.perf_counter()
        words, _ = transcribe_window(model, audio[start:end], start / 16000)
        if end != len(audio):
            words = tuple(word for word in words if word.end <= end / 16000 - 0.25)
        decode_seconds.append(time.perf_counter() - before)
        mentions.extend(ledger.accept(find_mentions(words, arguments.confidence), 0, end / 16000))
    report = {
        "model": arguments.model,
        "device": arguments.device,
        "audio_seconds": round(duration, 2),
        "processing_seconds": round(time.perf_counter() - started, 2),
        "slowest_window_seconds": round(max(decode_seconds, default=0), 2),
        "mentions": len(mentions),
        "expected": arguments.expected,
        "count_matches_expected": (
            len(mentions) == arguments.expected if arguments.expected is not None else None
        ),
        "detections": [asdict(mention) for mention in mentions],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 1 if report["count_matches_expected"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
