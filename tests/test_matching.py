import pytest

from vpn_counter.matching import Mention, MentionLedger, SpeechWord, find_mentions


@pytest.mark.parametrize(
    ("text", "count"),
    [
        ("A VPN biztonságos.", 1),
        ("VPN-t VPN-en VPN-ek VPN-es VPN-kapcsolat VPNnel", 6),
        ("OpenVPN NordVPN ProtonVPN ExpressVPN", 4),
        ("V P N és V.P.N. és v-p-n", 3),
        ("vé pé en, vé-pé-en, vépéen, ví pí en", 4),
        ("VPN, VPN! VPN?", 3),
        ("VPN‑t használok VPN–en keresztül.", 2),
        ("A végén a VPC hálózatán beszélünk, nem a VPM-ről.", 0),
        ("titkosítás kapcsolat hálózat magánhálózat", 0),
        ("Egy V vagy P vagy N betű nem elég.", 0),
    ],
)
def test_hungarian_forms_and_negative_speech(text, count):
    assert len(find_mentions((SpeechWord(text, 0, 3),))) == count


def test_spelled_acronym_uses_all_word_timestamps():
    words = (
        SpeechWord("A", 0, 0.2),
        SpeechWord("V", 0.2, 0.5),
        SpeechWord("P", 0.5, 0.8),
        SpeechWord("N-t", 0.8, 1.2),
        SpeechWord("használjuk", 1.2, 2),
    )
    result = find_mentions(words)
    assert len(result) == 1
    assert (result[0].start, result[0].end) == (0.2, 1.2)


def test_low_confidence_is_rejected():
    assert not find_mentions((SpeechWord("VPN", 1, 2, 0.2),), confidence=0.45)


def test_uncertain_letter_cannot_be_hidden_by_confident_surrounding_letters():
    words = (
        SpeechWord("vé", 1, 1.2, 0.99),
        SpeechWord("pé", 1.2, 1.4, 0.1),
        SpeechWord("en", 1.4, 1.6, 0.99),
    )
    assert not find_mentions(words, confidence=0.45)


@pytest.mark.parametrize(
    "word",
    [
        SpeechWord("VPN", 0, 0, 0.99),
        SpeechWord("VPN", 2, 1, 0.99),
        SpeechWord("VPN", 1, 2, float("nan")),
        SpeechWord("VPN", float("nan"), 2, 0.99),
    ],
)
def test_invalid_recognition_timing_and_confidence_cannot_increment_counter(word):
    assert not find_mentions((word,))


def test_overlapping_windows_count_each_observation_once():
    ledger = MentionLedger()
    first = Mention("VPN-t", 1, 1.6, 0.9)
    revised = Mention("VPN", 1.12, 1.72, 0.9)
    second = Mention("VPN-en", 3, 3.6, 0.9)
    assert ledger.accept([first], 0, 3) == [first]
    assert ledger.accept([revised, second], 0, 5) == [second]
    assert ledger.accept([second], 0, 7) == []


def test_fast_repetitions_in_one_window_are_preserved():
    ledger = MentionLedger()
    first = Mention("VPN", 1, 1.2, 0.9)
    second = Mention("VPN", 1.22, 1.42, 0.9)
    assert ledger.accept([first, second], 0, 3) == [first, second]
    assert ledger.accept([first, second], 0, 5) == []


def test_new_repetition_next_to_previously_seen_mention_counts():
    ledger = MentionLedger()
    first = Mention("VPN", 1, 1.2, 0.9)
    second = Mention("VPN", 1.22, 1.42, 0.9)
    ledger.accept([first], 0, 3)
    assert ledger.accept([first, second], 0, 5) == [second]


def test_resume_and_reset_invalidate_old_observations():
    ledger = MentionLedger()
    mention = Mention("VPN", 1, 2, 0.9)
    ledger.accept([mention], 0, 3)
    assert ledger.accept([mention], 1, 3) == [mention]
    ledger.clear()
    assert ledger.accept([mention], 1, 3) == [mention]
