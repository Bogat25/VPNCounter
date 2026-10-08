from types import SimpleNamespace

import numpy as np

from vpn_counter.engine import transcribe_window
from vpn_counter.matching import find_mentions


def test_non_speech_segments_cannot_increment_counter():
    class Model:
        def transcribe(self, audio, **kwargs):
            assert kwargs["language"] == "hu"
            assert kwargs["vad_filter"]
            assert kwargs["condition_on_previous_text"] is False
            hallucination = SimpleNamespace(
                no_speech_prob=0.95,
                avg_logprob=-0.1,
                text="VPN",
                words=[SimpleNamespace(word="VPN", start=0, end=1, probability=0.9)],
            )
            return iter([hallucination]), None

    words, text = transcribe_window(Model(), np.zeros(16000, dtype=np.float32))
    assert not find_mentions(words)
    assert text == ""


def test_word_times_are_offset_to_absolute_capture_timeline():
    class Model:
        def transcribe(self, audio, **kwargs):
            segment = SimpleNamespace(
                no_speech_prob=0.1,
                avg_logprob=-0.1,
                text="VPN-en",
                words=[SimpleNamespace(word="VPN-en", start=0.5, end=1, probability=0.9)],
            )
            return iter([segment]), None

    words, _ = transcribe_window(Model(), np.zeros(16000, dtype=np.float32), offset=10)
    mention = find_mentions(words)[0]
    assert (mention.start, mention.end) == (10.5, 11)
