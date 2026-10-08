from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass

# Accept the acronym, common VPN product compounds, separated letters, and the
# Hungarian/English letter names as Hungarian ASR may render them. Suffixes may
# attach directly or with a hyphen. Do not approximate unrelated Hungarian words.
_VPN = re.compile(
    r"(?<!\w)(?:"
    r"(?:open|nord|proton|express)?vpn"
    r"|v[\s.\-]+p[\s.\-]+n"
    r"|vé[\s.\-]*pé[\s.\-]*en"
    r"|ví[\s.\-]*pí[\s.\-]*en"
    r")[\w]*(?:[-\s]*-[\s]*[\w]+)*",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SpeechWord:
    text: str
    start: float
    end: float
    probability: float = 1.0


@dataclass(frozen=True, slots=True)
class Mention:
    text: str
    start: float
    end: float
    probability: float

    @property
    def center(self) -> float:
        return (self.start + self.end) / 2


@dataclass(frozen=True, slots=True)
class RecognitionBatch:
    words: tuple[SpeechWord, ...]
    text: str
    generation: int
    audio_end: float
    processing_seconds: float


def find_mentions(words: tuple[SpeechWord, ...], confidence: float = 0.45) -> list[Mention]:
    parts: list[str] = []
    spans: list[tuple[int, int, SpeechWord]] = []
    offset = 0
    for word in words:
        text = unicodedata.normalize("NFKC", word.text.strip())
        text = text.translate(str.maketrans({"‐": "-", "‑": "-", "–": "-", "—": "-"}))
        if not text:
            continue
        parts.append(text)
        spans.append((offset, offset + len(text), word))
        offset += len(text) + 1
    transcript = " ".join(parts)
    mentions: list[Mention] = []
    for match in _VPN.finditer(transcript):
        matched = [
            word for start, end, word in spans if start < match.end() and end > match.start()
        ]
        if not matched:
            continue
        if any(
            not all(math.isfinite(value) for value in (word.start, word.end, word.probability))
            or word.end <= word.start
            for word in matched
        ):
            continue
        # Every letter of a spelled acronym must be credible. Averaging lets
        # two confident letters hide a third that was barely recognized.
        probability = min(word.probability for word in matched)
        if probability < confidence:
            continue
        mentions.append(Mention(match.group(), matched[0].start, matched[-1].end, probability))
    return mentions


class MentionLedger:
    """Match repeated observations one-to-one across overlapping windows.

    All mentions inside a single result remain distinct, even when the presenter
    says VPN twice rapidly. Manual corrections do not remove these observations.
    """

    def __init__(self) -> None:
        self._seen: list[Mention] = []
        self._generation: int | None = None

    def clear(self) -> None:
        self._seen.clear()
        self._generation = None

    @staticmethod
    def _same(left: Mention, right: Mention) -> bool:
        overlap = max(0.0, min(left.end, right.end) - max(left.start, right.start))
        shorter = max(0.05, min(left.end - left.start, right.end - right.start))
        return overlap / shorter >= 0.45 or abs(left.center - right.center) <= 0.32

    def accept(self, mentions: list[Mention], generation: int, audio_end: float) -> list[Mention]:
        if generation != self._generation:
            self._seen.clear()
            self._generation = generation
        previous = [item for item in self._seen if item.end >= audio_end - 60]
        used: set[int] = set()
        accepted: list[Mention] = []
        for mention in mentions:
            matches = [
                (index, item)
                for index, item in enumerate(previous)
                if index not in used and self._same(mention, item)
            ]
            if matches:
                index, _ = min(matches, key=lambda pair: abs(pair[1].center - mention.center))
                used.add(index)
            else:
                accepted.append(mention)
        self._seen = previous + accepted
        return accepted
